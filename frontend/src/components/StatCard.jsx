export default function StatCard({ icon: Icon, value, label, color = 'var(--accent)', delay = 0 }) {
  return (
    <div className={`stat-card fade-up`} style={{ animationDelay: `${delay}s` }}>
      <div
        className="stat-icon"
        style={{
          background: `${color}18`,
          border: `1px solid ${color}30`,
        }}
      >
        {Icon && <Icon size={18} color={color} strokeWidth={2} />}
      </div>
      <div className="stat-value" style={{ color }}>
        {value ?? '—'}
      </div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
