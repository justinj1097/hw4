import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="container prose-page">
      <h1>Page not found</h1>
      <p className="lead">That page doesn't exist, but our hoodies do.</p>
      <Link className="btn btn-primary" to="/products">Shop all products</Link>
    </div>
  )
}
