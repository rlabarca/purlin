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
	cases := []struct {
		name string
		in   string
		ok   bool
	}{{"empty", "", true}, {"one", "a", true}}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			_, err := Parse(c.in)
			if (err == nil) != c.ok {
				t.Fatalf("Parse(%q) error = %v", c.in, err)
			}
		})
	}
}

// purlin: cart PROOF-3
func TestDiscount(t *testing.T) {
	t.Skip("no discounts yet")
}

// purlin: cart PROOF-4
func TestTotalIsWrong(t *testing.T) {
	if Total(2, 2) != 5 {
		t.Fatal("2 + 2 is not 5")
	}
}
