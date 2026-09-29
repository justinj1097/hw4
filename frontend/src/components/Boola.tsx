/**
 * Boola, the Campus Customs bulldog: the chat assistant's face.
 * Built only from HTML and CSS shapes (no image files), per the project rules for creatures.
 * mood: "idle" blinks now and then, "thinking" sniffs, "happy" wags its ears.
 */
export function Boola({ size = 44, mood = 'idle' }: { size?: number; mood?: 'idle' | 'thinking' | 'happy' }) {
  return (
    <span className={`boola boola-${mood}`} style={{ '--b': `${size}px` } as React.CSSProperties} aria-hidden="true">
      <span className="boola-ear left" />
      <span className="boola-ear right" />
      <span className="boola-head">
        <span className="boola-brow" />
        <span className="boola-eye left"><span className="boola-shine" /></span>
        <span className="boola-eye right"><span className="boola-shine" /></span>
        <span className="boola-muzzle">
          <span className="boola-nose" />
          <span className="boola-mouth" />
          <span className="boola-tooth left" />
          <span className="boola-tooth right" />
        </span>
      </span>
      <span className="boola-collar"><span className="boola-tag">Y</span></span>
    </span>
  )
}
