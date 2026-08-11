package health

import "testing"

func TestSuspend(t *testing.T) {
	q := New(0.4, 0.7)
	_ = q.Report("s1", "s2", 0.1)
	_ = q.Report("s3", "s2", 0.1)
	if q.CanVote("s2") {
		t.Fatal("s2 should be suspended")
	}
}

func TestSelfForbidden(t *testing.T) {
	q := New(0.4, 0.7)
	if err := q.Report("s1", "s1", 1); err == nil {
		t.Fatal("expected self-report error")
	}
}

func TestCorrelatedReportersShareOneDomainWeight(t *testing.T) {
	q := NewWithRecovery(0.3, 0.7, 2, 2)
	_, _ = q.ReportEvidence("cam-a", "fusion-1", 0.1, "rack-a", "")
	r, err := q.ReportEvidence("cam-b", "fusion-1", 0.9, "rack-a", "")
	if err != nil {
		t.Fatal(err)
	}
	if r.IndependentDomains != 1 || len(r.DomainWeights) != 1 {
		t.Fatalf("correlated reporters multiplied quorum weight: %+v", r)
	}
	d := r.DomainWeights[0]
	if d.FaultDomain != "rack-a" || len(d.Reporters) != 2 || d.Reporters[0] != "cam-a" || d.Reporters[1] != "cam-b" {
		t.Fatalf("unexpected domain receipt: %+v", d)
	}
	if d.DomainHealth != 0.5 || d.EffectiveWeight != 1.0 {
		t.Fatalf("unexpected domain weight: %+v", d)
	}
}

func TestIndependentDomainsHaveExplainableEqualWeight(t *testing.T) {
	q := NewWithRecovery(0.2, 0.8, 2, 2)
	_, _ = q.ReportEvidence("a1", "sensor-x", 0.2, "rack-a", "")
	_, _ = q.ReportEvidence("a2", "sensor-x", 0.4, "rack-a", "")
	r, err := q.ReportEvidence("b1", "sensor-x", 0.9, "rack-b", "")
	if err != nil {
		t.Fatal(err)
	}
	if r.IndependentDomains != 2 || len(r.DomainWeights) != 2 {
		t.Fatalf("want two domains: %+v", r)
	}
	if r.DomainWeights[0].EffectiveWeight != 0.5 || r.DomainWeights[1].EffectiveWeight != 0.5 {
		t.Fatalf("weights are not explainable/equal: %+v", r.DomainWeights)
	}
}

func TestCorrelatedMultiplicityCannotFakeRecovery(t *testing.T) {
	q := NewWithRecovery(0.4, 0.55, 2, 2)
	_, _ = q.ReportEvidence("bad", "sensor-x", 0.0, "rack-a", "")
	if q.CanVote("sensor-x") {
		t.Fatal("sensor-x should be suspended")
	}
	var r DecisionReceipt
	for _, reporter := range []string{"good-1", "good-2", "good-3"} {
		r, _ = q.ReportEvidence(reporter, "sensor-x", 1.0, "rack-a", "round-1")
	}
	if r.IndependentDomains != 1 || r.Reason != "INSUFFICIENT_INDEPENDENT_DOMAINS" || r.RecoveryStreak != 0 {
		t.Fatalf("correlated multiplicity faked recovery: %+v", r)
	}
	if q.CanVote("sensor-x") {
		t.Fatal("sensor-x should remain suspended")
	}
}

func TestRecoveryRequiresDistinctRoundsAndIndependentDomains(t *testing.T) {
	q := NewWithRecovery(0.4, 0.6, 2, 2)
	_, _ = q.ReportEvidence("a", "sensor-x", 0.0, "rack-a", "")
	_, _ = q.ReportEvidence("b", "sensor-x", 0.0, "rack-b", "")
	_, _ = q.ReportEvidence("a", "sensor-x", 1.0, "rack-a", "")
	noRound, _ := q.ReportEvidence("b", "sensor-x", 1.0, "rack-b", "")
	if noRound.Reason != "ROUND_ID_REQUIRED_FOR_RECOVERY" {
		t.Fatalf("recovery advanced without round identity: %+v", noRound)
	}
	first, _ := q.ReportEvidence("a", "sensor-x", 1.0, "rack-a", "r1")
	if first.RecoveryStreak != 1 || q.CanVote("sensor-x") {
		t.Fatalf("first round must hold: %+v", first)
	}
	duplicate, _ := q.ReportEvidence("b", "sensor-x", 1.0, "rack-b", "r1")
	if duplicate.RecoveryStreak != 1 || q.CanVote("sensor-x") {
		t.Fatalf("duplicate round advanced recovery: %+v", duplicate)
	}
	second, _ := q.ReportEvidence("a", "sensor-x", 1.0, "rack-a", "r2")
	if second.Transition != "REINSTATE" || second.Reason != "RECOVERY_HYSTERESIS_SATISFIED" || !q.CanVote("sensor-x") {
		t.Fatalf("second distinct round should reinstate: %+v", second)
	}
}

func TestLastReceiptIsObservable(t *testing.T) {
	q := New(0.4, 0.7)
	_, _ = q.ReportEvidence("a", "sensor-x", 0.1, "rack-a", "")
	r, ok := q.LastReceipt("sensor-x")
	if !ok || r.Subject != "sensor-x" || r.Reason == "" {
		t.Fatalf("missing explainable receipt: %+v %v", r, ok)
	}
}

func TestEmptyFaultDomainFailsClosed(t *testing.T) {
	q := New(0.4, 0.7)
	if _, err := q.ReportEvidence("a", "sensor-x", 0.5, "", ""); err == nil {
		t.Fatal("expected fault-domain error")
	}
}
