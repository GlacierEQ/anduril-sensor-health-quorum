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
