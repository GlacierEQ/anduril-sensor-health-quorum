package health

import "testing"

func TestSuspendAndSelfReport(t *testing.T) {
	q := New(0.4, 0.7)
	_ = q.Report("s1", "s2", 0.1)
	_ = q.Report("s3", "s2", 0.1)
	if q.CanVote("s2") {
		t.Fatal("s2 should be suspended")
	}
	if err := q.Report("s1", "s1", 1); err == nil {
		t.Fatal("expected self-report error")
	}
}

func TestCorrelatedReportersCountAsOneDomain(t *testing.T) {
	q := NewWithRecovery(0.3, 0.7, 2, 2)
	_, _ = q.ReportEvidence("cam-a", "fusion", 0.1, "rack-a", "")
	r, err := q.ReportEvidence("cam-b", "fusion", 0.9, "rack-a", "")
	if err != nil {
		t.Fatal(err)
	}
	if r.IndependentDomains != 1 || len(r.DomainWeights) != 1 {
		t.Fatalf("correlated reporters multiplied quorum weight: %+v", r)
	}
	if len(r.DomainWeights[0].Reporters) != 2 || r.DomainWeights[0].EffectiveWeight != 1.0 {
		t.Fatalf("unexpected domain receipt: %+v", r.DomainWeights[0])
	}
}

func TestCorrelatedMultiplicityCannotReinstate(t *testing.T) {
	q := NewWithRecovery(0.4, 0.55, 2, 2)
	_, _ = q.ReportEvidence("bad", "sensor-x", 0.0, "rack-a", "")
	var r DecisionReceipt
	for _, reporter := range []string{"good-1", "good-2", "good-3"} {
		r, _ = q.ReportEvidence(reporter, "sensor-x", 1.0, "rack-a", "round-1")
	}
	if r.IndependentDomains != 1 || r.Reason != "INSUFFICIENT_INDEPENDENT_DOMAINS" {
		t.Fatalf("correlated multiplicity faked independence: %+v", r)
	}
	if q.CanVote("sensor-x") {
		t.Fatal("sensor-x should remain suspended")
	}
}

func TestRecoveryRequiresThresholdThenDistinctRounds(t *testing.T) {
	q := NewWithRecovery(0.4, 0.6, 2, 2)
	_, _ = q.ReportEvidence("a", "sensor-x", 0.0, "rack-a", "")
	_, _ = q.ReportEvidence("b", "sensor-x", 0.0, "rack-b", "")
	_, _ = q.ReportEvidence("a", "sensor-x", 1.0, "rack-a", "")
	below, _ := q.ReportEvidence("b", "sensor-x", 1.0, "rack-b", "")
	if below.Reason != "RECOVERY_THRESHOLD_NOT_MET" {
		t.Fatalf("expected threshold hold: %+v", below)
	}
	noRound, _ := q.ReportEvidence("a", "sensor-x", 1.0, "rack-a", "")
	if noRound.SmoothedScore < q.ReinstateAbove || noRound.Reason != "ROUND_ID_REQUIRED_FOR_RECOVERY" {
		t.Fatalf("expected round-id gate after threshold: %+v", noRound)
	}
	first, _ := q.ReportEvidence("a", "sensor-x", 1.0, "rack-a", "r1")
	duplicate, _ := q.ReportEvidence("b", "sensor-x", 1.0, "rack-b", "r1")
	second, _ := q.ReportEvidence("a", "sensor-x", 1.0, "rack-a", "r2")
	if first.RecoveryStreak != 1 || duplicate.RecoveryStreak != 1 {
		t.Fatalf("duplicate round advanced recovery: %+v %+v", first, duplicate)
	}
	if second.Transition != "REINSTATE" || !q.CanVote("sensor-x") {
		t.Fatalf("second distinct round should reinstate: %+v", second)
	}
}

func TestReceiptAndInvalidDomain(t *testing.T) {
	q := New(0.4, 0.7)
	_, _ = q.ReportEvidence("a", "sensor-x", 0.1, "rack-a", "")
	if receipt, ok := q.LastReceipt("sensor-x"); !ok || receipt.Reason == "" {
		t.Fatalf("missing explainable receipt: %+v %v", receipt, ok)
	}
	if _, err := q.ReportEvidence("a", "sensor-y", 0.5, "", ""); err == nil {
		t.Fatal("expected fault-domain error")
	}
}
