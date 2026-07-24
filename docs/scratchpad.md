August Expiry Calender (Commodity )
August Nifty bank nifty sensex weekly
bank holiday 1 day before and on day raat ko 12 baje  live kardena 
market holiday 1 day before and on day raat ko 12 baje  live kardena
ipo market listing and ipo launch
~~morning market summary (put call oi ratio, top gainer or looser, suuport resistance (nifty/sensex).)~~
mid summary
closing summary
stock of the day 
https://hdfcsky.com/news



Should have table.....idk
IPO blogs should have quantititaive words when listed at market
https://www.swastika.co.in/blog/millworks-technologies-ipo-a-retail-investor-guide-to-a-blockbuster-sme-debut





Kapil Feedbacks
Center Aligned text on outer blog images
anchor text linked external references
Capitalization

---

## 2026-07-23 -- Proprietary trading data in blogs -- ON HOLD (compliance)

Idea: query Capsfo.dbo.trade1dataexport (SQL Server, "18 server") for which
segment (COMPANY_CODE) had the most trades, and feed that into blog
generation as real in-house trading-activity commentary.

Dropped for now -- compliance concerns raised before any connection was made
(no DB credentials were requested or used):
- trade1dataexport has CLIENT_ID -- real client trade records, not anonymous
  market data. Broker-client confidentiality duty covers this.
- DPDP Act 2023 purpose limitation: data collected for trade execution
  can't just be repurposed for content/marketing without a separate basis.
- Even aggregated, "which segment traded most" reflects only this firm's
  own client base, not the market -- risk of reading as a market-wide
  stat in a blog when it isn't one (SEBI conduct/advertising code risk).
- Possible Chinese-wall/conflict-of-interest issue if proprietary trade-flow
  data feeds content published by a research/advisory arm.

Needs explicit written sign-off from compliance/legal before revisiting --
specifically whether client-level trade data can be used for this at all
under client agreements + DPDP Act, and what aggregation/anonymization/
disclosure would be required if so. Do not pick this back up without that.