# Captured test reports

Each folder here holds a small test source file and the report its framework
wrote for it, read by `dev/test_reports.py`:

- `jest/`: jest 29.7.0 with jest-junit 16.0.0, run with the command
  `purlin:init` writes for jest.
- `vitest/`: Vitest 3.2.7 with its own `junit` reporter.
- `dotnet/`: `dotnet test --logger trx` on .NET 8 with xUnit 2.9.2.
- `go/`: `go test -json ./...`, the command `purlin:init` writes for Go, on
  Go 1.27.1 over a module of two packages, one of whose tests panics.

Absolute paths and host names in the reports are replaced with
`/home/dev/project` and `dev-machine`, and Go's own install path with
`/usr/local/go`.
