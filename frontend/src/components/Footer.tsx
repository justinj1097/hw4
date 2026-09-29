const YEAR = new Date().getFullYear()

export function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-grid">
        <div>
          <p className="footer-brand">Campus Customs</p>
          <p>New Haven's oldest official Yale merchandise store, printing and embroidering on site since 1975.</p>
          <p className="licensed">Officially Licensed Merchandise</p>
        </div>
        <div>
          <p className="footer-head">Visit</p>
          <p>57 Broadway<br />New Haven, CT 06511</p>
          <p>Call ahead for hours: (475) 301-4205</p>
        </div>
        <div>
          <p className="footer-head">Orders &amp; returns</p>
          <p>Returns within 30 days of shipping, unworn with tags. Custom items are final sale.</p>
          <p>
            <a href="mailto:orderdept@campuscustoms.com">orderdept@campuscustoms.com</a>
          </p>
        </div>
        <div>
          <p className="footer-head">Shop online</p>
          <p>
            <a href="https://yalebulldogblue.com" target="_blank" rel="noreferrer">yalebulldogblue.com</a>
          </p>
          <p>Most orders are produced in 5–8 business days and ship via UPS.</p>
        </div>
      </div>
      <div className="container footer-bottom">© {YEAR} Campus Customs · Class project demo storefront</div>
    </footer>
  )
}
