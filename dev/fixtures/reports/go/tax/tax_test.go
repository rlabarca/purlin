package tax

import "testing"

// purlin: tax PROOF-1
func TestRate(t *testing.T) {
	if Rate("uk") != 0.2 {
		t.Fatal("uk rate")
	}
}

// purlin: tax PROOF-2
func TestLookupPanics(t *testing.T) {
	Lookup([]float64{}, 3)
}

// purlin: tax PROOF-3
func TestAfterThePanic(t *testing.T) {
}
