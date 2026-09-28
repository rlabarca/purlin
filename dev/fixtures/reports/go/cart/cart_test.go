package cart

import "testing"

// purlin: cart PROOF-1
func TestTotal(t *testing.T) {
	if Total(2, 3) != 5 {
		t.Fatal("wrong total")
	}
}

// purlin: cart PROOF-2
func TestParse(t *testing.T) {
	t.Run("empty", func(t *testing.T) {
		if _, err := Parse(""); err == nil {
			t.Fatal("an empty basket parsed")
		}
	})
	t.Run("one", func(t *testing.T) {})
}

// purlin: cart PROOF-3
func TestDiscount(t *testing.T) {
	t.Skip("no discounts yet")
}
