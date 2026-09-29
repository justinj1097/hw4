import { useEffect } from 'react'
import { Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { ChatPanel } from './components/ChatPanel'
import { ChatShowcase } from './components/ChatShowcase'
import { Footer } from './components/Footer'
import { SiteHeader } from './components/SiteHeader'
import { AboutPage } from './pages/AboutPage'
import { AuthPage } from './pages/AuthPage'
import { HomePage } from './pages/HomePage'
import { NotFoundPage } from './pages/NotFoundPage'
import { ProductPage } from './pages/ProductPage'
import { ProductsPage } from './pages/ProductsPage'
import { SavedPage } from './pages/SavedPage'
import { ShopProvider } from './store'

/** Header and nav on top, the page in the middle, footer below, and the floating chat on every page. */
function Layout() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo({ top: 0 })
  }, [pathname])
  return (
    <div className="page">
      <SiteHeader />
      <main>
        <ChatShowcase />
        <div className="page-fade" key={pathname}>
          <Outlet />
        </div>
      </main>
      <Footer />
      <ChatPanel />
    </div>
  )
}

export default function App() {
  return (
    <ShopProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="products" element={<ProductsPage />} />
          <Route path="products/:productId" element={<ProductPage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="saved" element={<SavedPage />} />
          <Route path="login" element={<AuthPage mode="login" />} />
          <Route path="signup" element={<AuthPage mode="signup" />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </ShopProvider>
  )
}
