import { Link } from 'react-router-dom'

export function AboutPage() {
  return (
    <div className="container prose-page">
      <p className="eyebrow dark">About Us</p>
      <h1>A New Haven family shop since 1975</h1>
      <p className="lead">
        Campus Customs started as a small Yale memorabilia shop across the street from campus. Nearly fifty years later
        the same store is still open at 57 Broadway, and the family that founded it still runs it.
      </p>

      <div className="about-grid">
        <section>
          <h2>What we do</h2>
          <p>
            We are New Haven's longest-running official Yale merchandise retailer. Our shelves carry hoodies, crewnecks,
            tees, quarter-zips, and jackets for Yale College, the residential colleges, the graduate and professional
            schools, and Bulldog athletics. There's also relative gear for proud moms, dads, and grandparents.
          </p>
          <p>
            Because our production space sits right beside the store, most screen printing and embroidery is done in-house.
            That keeps turnaround quick and lets us take on custom work for teams, clubs, reunions, and campus events.
          </p>
        </section>
        <section>
          <h2>Officially licensed</h2>
          <p>
            Every Yale mark we sell is licensed by the university. When you buy from us, you know the crest, the Big Y, and
            the bulldog are the real thing.
          </p>
          <h2>Shop in person or online</h2>
          <p>
            Visit us at 57 Broadway, New Haven, CT 06511, or shop our online store at{' '}
            <a href="https://yalebulldogblue.com" target="_blank" rel="noreferrer">yalebulldogblue.com</a>. Online orders are
            usually made within 5–8 business days and ship by UPS, and we ship internationally too.
          </p>
        </section>
      </div>

      <section className="policy-box">
        <h2>Returns, in plain English</h2>
        <ul>
          <li>Send items back within 30 days of shipping, unworn and with the tags still on.</li>
          <li>If we made a mistake, we pay for the return. Otherwise return shipping is on you.</li>
          <li>Custom pieces, such as Custom Alumni items, are made just for you and are final sale.</li>
          <li>Refunds exclude the original shipping cost and can take 2–10 business days to reach your bank.</li>
        </ul>
        <p className="muted">
          Questions about an order? Call (475) 301-4205 or email{' '}
          <a href="mailto:orderdept@campuscustoms.com">orderdept@campuscustoms.com</a>.
        </p>
      </section>

      <Link className="btn btn-primary" to="/products">Browse the collection</Link>
    </div>
  )
}
