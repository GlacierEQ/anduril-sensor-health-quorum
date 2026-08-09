package health

import "sync"

// Quorum tracks peer health with suspend/reinstate thresholds.
type Quorum struct {
	mu             sync.Mutex
	scores         map[string]float64
	suspended      map[string]struct{}
	SuspendBelow   float64
	ReinstateAbove float64
}

func New(suspendBelow, reinstateAbove float64) *Quorum {
	return &Quorum{
		scores: make(map[string]float64), suspended: make(map[string]struct{}),
		SuspendBelow: suspendBelow, ReinstateAbove: reinstateAbove,
	}
}

func (q *Quorum) Report(reporter, subject string, h float64) error {
	if reporter == subject {
		return errSelf
	}
	if h < 0 || h > 1 {
		return errRange
	}
	q.mu.Lock()
	defer q.mu.Unlock()
	prev := 0.5
	if v, ok := q.scores[subject]; ok {
		prev = v
	}
	q.scores[subject] = 0.6*prev + 0.4*h
	if q.scores[subject] < q.SuspendBelow {
		q.suspended[subject] = struct{}{}
	} else if q.scores[subject] >= q.ReinstateAbove {
		delete(q.suspended, subject)
	}
	return nil
}

func (q *Quorum) CanVote(id string) bool {
	q.mu.Lock()
	defer q.mu.Unlock()
	_, sus := q.suspended[id]
	return !sus
}

type simpleError string

func (e simpleError) Error() string { return string(e) }

const errSelf = simpleError("SELF_REPORT_FORBIDDEN")
const errRange = simpleError("HEALTH_RANGE")
