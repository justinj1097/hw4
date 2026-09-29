import { Link, NavLink, useNavigate } from 'react-router-dom'
import { SearchBox } from './SearchBox'
import { useShop } from '../store'

const navClass = ({ isActive }: { isActive: boolean }) => (isActive ? 'active' : '')

export function SiteHeader() {
  const { user, signOut, saved } = useShop()
  const navigate = useNavigate()

  return (
    <header className="site-header">
      <div className="announcement" aria-label="Officially Licensed Yale Merchandise · 57 Broadway, New Haven since 1975">
        <div className="ticker" aria-hidden="true">
          {[0, 1].map((copy) => (
            <span key={copy} className="ticker-run">
              <span>Officially licensed Yale merchandise</span><span>★</span><span>Printed &amp; stitched on Broadway</span><span>★</span>
              <span>Returns within 30 days</span><span>★</span><span>Ships nationwide via UPS</span><span>★</span>
              <span>Ask Boola about sizes &amp; stock</span><span>★</span><span>Boola boola!</span><span>★</span>
            </span>
          ))}
        </div>
      </div>
      <div className="header-main container">
        <Link className="logo" to="/" aria-label="Campus Customs home">
          <span className="logo-mark">Y</span>
          <span className="logo-text">
            <span className="logo-name">Campus Customs</span>
            <span className="logo-sub">Yale Bulldog Blue</span>
          </span>
        </Link>
        <SearchBox />
      </div>
      <nav className="main-nav" aria-label="Main">
        <div className="container nav-row">
          <NavLink to="/" end className={navClass}>Home</NavLink>
          <NavLink to="/products" className={navClass}>Products</NavLink>
          <NavLink to="/about" className={navClass}>About Us</NavLink>
          <span className="nav-spacer" />
          <NavLink to="/saved" className={({ isActive }) => `nav-saved ${isActive ? 'active' : ''}`} aria-label={`Saved items (${saved.length})`}>
            ♡ Saved{saved.length > 0 && <span className="count-badge">{saved.length}</span>}
          </NavLink>
          {user ? (
            <>
              <span className="nav-hello">Hi, {user.first_name}</span>
              <button className="nav-button" onClick={() => { signOut(); navigate('/') }}>Sign out</button>
            </>
          ) : (
            <>
              <NavLink to="/login" className={navClass}>Log in</NavLink>
              <NavLink to="/signup" className={({ isActive }) => `nav-cta ${isActive ? 'active' : ''}`}>Create Account</NavLink>
            </>
          )}
        </div>
      </nav>
    </header>
  )
}
