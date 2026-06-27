interface AreaScoreBadgeProps {
  score: number;
}

export function AreaScoreBadge({ score }: AreaScoreBadgeProps) {
  return (
    <div aria-label={`Civic Health ${score} out of 100`} className="area-score-ring">
      <strong>{score}</strong>
      <span>/100</span>
    </div>
  );
}
