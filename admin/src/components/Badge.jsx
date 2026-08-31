export default function Badge({ children, variant = 'default' }) {
  const variants = {
    default: 'bg-white/10 text-muted',
    success: 'bg-success/15 text-success',
    warning: 'bg-warning/15 text-warning',
    danger: 'bg-danger/15 text-danger',
    accent: 'bg-accent/15 text-accent',
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${variants[variant]}`}
    >
      {children}
    </span>
  )
}

export function PlanBadge({ plan }) {
  const planVariants = {
    PRO: 'accent',
    DJ_ARCHIVE: 'warning',
    STUDIO: 'success',
    ENTERPRISE: 'accent',
    DEMO: 'default',
  }
  return <Badge variant={planVariants[plan] || 'default'}>{plan}</Badge>
}

export function StatusBadge({ status }) {
  const statusVariants = {
    active: 'success',
    past_due: 'warning',
    cancelled: 'danger',
    trialing: 'accent',
    incomplete: 'default',
    incomplete_expired: 'danger',
  }
  return <Badge variant={statusVariants[status] || 'default'}>{status}</Badge>
}
