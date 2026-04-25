export function Calculator({ formula }: { formula: string }) {
  const result = eval(formula);
  return <p>{result}</p>;
}
