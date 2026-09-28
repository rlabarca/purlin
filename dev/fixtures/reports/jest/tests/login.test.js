// purlin: login PROOF-1
test('accepts', () => { expect(1).toBe(1); });

describe('outer', () => {
  describe('inner', () => {
    // purlin: login PROOF-2
    it('same name', () => { expect(1).toBe(1); });
  });
  it('same name', () => { expect(1).toBe(2); });
  // purlin: login PROOF-3
  it.skip('skipped', () => {});
  // purlin: login PROOF-4
  test.each([1, 2])('param %i', (x) => { expect(x).toBeGreaterThan(0); });
});
