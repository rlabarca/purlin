using Xunit;

namespace App.Tests {
  public class GreetingTests {
    // purlin: greeting PROOF-1
    [Fact]
    public void GreetsByName() { Assert.Equal(1, 1); }

    // purlin: greeting PROOF-2
    [Theory]
    [InlineData(1)]
    [InlineData(2)]
    public void Param(int x) { Assert.True(x > 1); }

    // purlin: greeting PROOF-3
    [Fact(Skip = "no")]
    public void Skipped() { }

    public class Nested {
      // purlin: greeting PROOF-4
      [Fact]
      public void Inner() { Assert.Equal(1, 1); }
    }
  }
}
