export default function StatsCard({ title, value, icon: Icon, accent = 'accent', subtitle }) {
  const accentColors = {
    accent: 'text-accent bg-accent/10',
    success: 'text-success bg-success/10',
    warning: 'text-warning bg-warning/10',
    muted: 'text-muted bg-white/5',
  }

  return (
    <div className="bg-card rounded-xl p-5 border border-white/5 hover:border-white/10 transition-colors">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-muted">{title}</p>
          <p className="text-3xl font-bold mt-1">{value}</p>
          {subtitle && <p className="text-xs text-muted mt-1">{subtitle}</p>}
        </div>
        {Icon && (
          <div className={`p-3 rounded-lg ${accentColors[accent]}`}>
            <Icon size={24} />
          </div>
        )}
      </div>
    </div>
  )
}