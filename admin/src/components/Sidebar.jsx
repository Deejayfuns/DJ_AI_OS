import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Users, KeyRound, CreditCard, FileText, LogOut, Menu, X, UserPlus
} from 'lucide-react'
import { useState } from 'react'

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/customers', label: 'Customers', icon: UserPlus },
  { path: '/users', label: 'Users', icon: Users },
  { path: '/licenses', label: 'Licenses', icon: KeyRound },
  { path: '/subscriptions', label: 'Subscriptions', icon: CreditCard },
  { path: '/audit', label: 'Audit Log', icon: FileText },
]

export default function Sidebar({ onLogout }) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className={`flex flex-col bg-panel border-r border-white/10 transition-all duration-300 ${
        collapsed ? 'w-16' : 'w-64'
      }`}
    >
      <div className="flex items-center justify-between h-16 px-4 border-b border-white/10">
        {!collapsed && (
          <span className="font-bold text-lg text-accent flex items-center gap-2">
            <span className="w-8 h-8 rounded bg-accent/20 flex items-center justify-center">
              <span className="text-xs">DJ</span>
            </span>
            DJ AI OS
          </span>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-2 rounded hover:bg-white/10 text-muted"
        >
          {collapsed ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      <nav className="flex-1 px-2 py-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                isActive
                  ? 'bg-accent/10 text-accent'
                  : 'text-muted hover:text-text hover:bg-white/5'
              }`
            }
          >
            <item.icon size={20} />
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-white/10">
        <button
          onClick={onLogout}
          className={`flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-muted hover:text-danger hover:bg-white/5 transition-colors ${
            collapsed ? 'justify-center' : ''
          }`}
          title="Logout"
        >
          <LogOut size={20} />
          {!collapsed && <span>Logout</span>}
        </button>
      </div>
    </aside>
  )
}