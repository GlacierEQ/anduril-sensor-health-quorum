package health

import (
	"sort"
	"sync"
)

type Evidence struct {
	Reporter    string
	Subject     string
	Health      float64
	FaultDomain string
	RoundID     string
}

type DomainWeight struct {
	FaultDomain     string
	Reporters       []string
	DomainHealth    float64
	EffectiveWeight float64
}

type DecisionReceipt struct {
	Subject                string
	ObservedHealth         float64
	SmoothedScore          float64
	IndependentDomains     int
	DomainWeights          []DomainWeight
	SuspendedBefore        bool
	SuspendedAfter         bool
	Transition             string
	RecoveryStreak         int
	RequiredRecoveryRounds int
	Reason                 string
}

// Quorum tracks peer health with correlation-aware weighting and bounded recovery.
type Quorum struct {
	mu                     sync.Mutex
	scores                 map[string]float64
	suspended              map[string]struct{}
	evidence               map[string]map[string]Evidence
	recoveryStreaks        map[string]int
	recoveryRoundsSeen     map[string]map[string]struct{}
	receipts               map[string]DecisionReceipt
	SuspendBelow           float64
	ReinstateAbove         float64
	RequiredRecoveryRounds int
	MinRecoveryDomains     int
}

func New(suspendBelow, reinstateAbove float64) *Quorum {
	return NewWithRecovery(suspendBelow, reinstateAbove, 2, 2)
}

func NewWithRecovery(suspendBelow, reinstateAbove float64, requiredRounds, minDomains int) *Quorum {
	if suspendBelow < 0 || suspendBelow >= reinstateAbove || reinstateAbove > 1 {
		panic("invalid thresholds")
	}
	if requiredRounds <= 0 || minDomains <= 0 {
		panic("invalid recovery configuration")
	}
	return &Quorum{
		scores:                 make(map[string]float64),
		suspended:              make(map[string]struct{}),
		evidence:               make(map[string]map[string]Evidence),
		recoveryStreaks:        make(map[string]int),
		recoveryRoundsSeen:     make(map[string]map[string]struct{}),
		receipts:               make(map[string]DecisionReceipt),
		SuspendBelow:           suspendBelow,
		ReinstateAbove:         reinstateAbove,
		RequiredRecoveryRounds: requiredRounds,
		MinRecoveryDomains:     minDomains,
	}
}

// Report preserves the original API. Reporter identity is its default independent
// fault domain and recovery does not advance without an explicit round ID.
func (q *Quorum) Report(reporter, subject string, h float64) error {
	_, err := q.ReportEvidence(reporter, subject, h, reporter, "")
	return err
}

func (q *Quorum) ReportEvidence(reporter, subject string, h float64, faultDomain, roundID string) (DecisionReceipt, error) {
	if reporter == "" || subject == "" {
		return DecisionReceipt{}, errSensorID
	}
	if reporter == subject {
		return DecisionReceipt{}, errSelf
	}
	if h < 0 || h > 1 {
		return DecisionReceipt{}, errRange
	}
	if faultDomain == "" {
		return DecisionReceipt{}, errFaultDomain
	}

	q.mu.Lock()
	defer q.mu.Unlock()

	if _, ok := q.evidence[subject]; !ok {
		q.evidence[subject] = make(map[string]Evidence)
	}
	q.evidence[subject][reporter] = Evidence{
		Reporter: reporter, Subject: subject, Health: h, FaultDomain: faultDomain, RoundID: roundID,
	}
	weights := q.domainWeights(subject)
	observed := 0.0
	for _, row := range weights {
		observed += row.DomainHealth * row.EffectiveWeight
	}
	prev := 0.5
	if value, ok := q.scores[subject]; ok {
		prev = value
	}
	score := 0.6*prev + 0.4*observed
	q.scores[subject] = score
	_, wasSuspended := q.suspended[subject]
	transition := "UNCHANGED"
	reason := "HEALTH_ACCEPTABLE"

	if score < q.SuspendBelow {
		q.suspended[subject] = struct{}{}
		q.recoveryStreaks[subject] = 0
		q.recoveryRoundsSeen[subject] = make(map[string]struct{})
		if wasSuspended {
			transition = "HOLD_SUSPENDED"
		} else {
			transition = "SUSPEND"
		}
		reason = "BELOW_SUSPEND_THRESHOLD"
	} else if wasSuspended {
		if score < q.ReinstateAbove {
			q.recoveryStreaks[subject] = 0
			reason = "RECOVERY_THRESHOLD_NOT_MET"
		} else if len(weights) < q.MinRecoveryDomains {
			q.recoveryStreaks[subject] = 0
			reason = "INSUFFICIENT_INDEPENDENT_DOMAINS"
		} else if roundID == "" {
			reason = "ROUND_ID_REQUIRED_FOR_RECOVERY"
		} else {
			if _, ok := q.recoveryRoundsSeen[subject]; !ok {
				q.recoveryRoundsSeen[subject] = make(map[string]struct{})
			}
			if _, seen := q.recoveryRoundsSeen[subject][roundID]; !seen {
				q.recoveryRoundsSeen[subject][roundID] = struct{}{}
				q.recoveryStreaks[subject]++
			}
			if q.recoveryStreaks[subject] >= q.RequiredRecoveryRounds {
				delete(q.suspended, subject)
				transition = "REINSTATE"
				reason = "RECOVERY_HYSTERESIS_SATISFIED"
			} else {
				transition = "HOLD_SUSPENDED"
				reason = "RECOVERY_HYSTERESIS_INCOMPLETE"
			}
		}
	}

	_, isSuspended := q.suspended[subject]
	receipt := DecisionReceipt{
		Subject: subject, ObservedHealth: observed, SmoothedScore: score,
		IndependentDomains: len(weights), DomainWeights: weights,
		SuspendedBefore: wasSuspended, SuspendedAfter: isSuspended,
		Transition: transition, RecoveryStreak: q.recoveryStreaks[subject],
		RequiredRecoveryRounds: q.RequiredRecoveryRounds, Reason: reason,
	}
	q.receipts[subject] = receipt
	return receipt, nil
}

func (q *Quorum) domainWeights(subject string) []DomainWeight {
	grouped := make(map[string][]Evidence)
	for _, report := range q.evidence[subject] {
		grouped[report.FaultDomain] = append(grouped[report.FaultDomain], report)
	}
	if len(grouped) == 0 {
		return nil
	}
	domains := make([]string, 0, len(grouped))
	for domain := range grouped {
		domains = append(domains, domain)
	}
	sort.Strings(domains)
	weight := 1.0 / float64(len(domains))
	rows := make([]DomainWeight, 0, len(domains))
	for _, domain := range domains {
		reports := grouped[domain]
		reporters := make([]string, 0, len(reports))
		total := 0.0
		for _, report := range reports {
			reporters = append(reporters, report.Reporter)
			total += report.Health
		}
		sort.Strings(reporters)
		rows = append(rows, DomainWeight{
			FaultDomain: domain, Reporters: reporters,
			DomainHealth: total / float64(len(reports)), EffectiveWeight: weight,
		})
	}
	return rows
}

func (q *Quorum) CanVote(id string) bool {
	q.mu.Lock()
	defer q.mu.Unlock()
	_, suspended := q.suspended[id]
	return !suspended
}

func (q *Quorum) LastReceipt(id string) (DecisionReceipt, bool) {
	q.mu.Lock()
	defer q.mu.Unlock()
	receipt, ok := q.receipts[id]
	return receipt, ok
}

type simpleError string

func (e simpleError) Error() string { return string(e) }

const errSelf = simpleError("SELF_REPORT_FORBIDDEN")
const errRange = simpleError("HEALTH_RANGE")
const errSensorID = simpleError("SENSOR_ID")
const errFaultDomain = simpleError("FAULT_DOMAIN")
