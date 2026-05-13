import json
from add_cached import cached_model_call



def generate_notification(item):
    prompt = f"""
You are a fintech push notification copywriter.

Create a catchy, user-focused mobile notification. It should have a hook and the CTA (which is trade on swastika app) should be very cohesive with the hook.
It could be trade on swastika app or invest thorugh swastika app or invest in mutual fund though swastika app or trade in futures or options for swastika app.

The Call to Action should be VERY VERY cohesive with the hook you're using for mobile notification

Blog Title: {item['Blog_Title']}
Blog Content: {item['Blog_Content']}

Rules:
- Max 130 characters
- Write ONLY ONE smooth sentence
- Start with a strong hook
- keep it engaging 
- Include a natural call-to-action mentioning Swastika app
- CTA must feel smooth and part of the sentence (NOT forced)
- Use soft, catchy CTA words.
- The sentence should feel like a real app notification, not an advertisement
- Simple, human-like English
- No hashtags
- No \\n

Output ONLY JSON:
{{
  "blog_notify": ""
}}



One Shot examples which you could refer and create your own push app notifications are:
1. 
    Input: 
        Blog Title : Bank of Maharashtra Q4 Results: Net profit up 34% YoY and NII up 20%
        Blog Content: <H1>Bank of Maharashtra Q4 Results: Net profit jumps 34% YoY to Rs 2,014 crore; NII up 20%</H1><H2>Overview and what the numbers indicate</H2><P>The Bank of Maharashtra reported in its Q4FY26 results a net profit of Rs 2,014 crore, up 34% year over year, supported by a 20% rise in net interest income NII and a stronger loan portfolio. This performance translates to improvement in both profitability and revenue diversification for a public sector lender with a long history in India. For the full year FY26 the bank also posted a solid growth trajectory across deposits and advances indicating steady customer acquisition and saver behavior within a cautious macroeconomic backdrop.</P><H2>Key drivers behind the numbers</H2><H3>NII growth and loan book momentum</H3><P>The 20% growth in net interest income reflects a combination of higher yields on lending, better loan mix, and favourable funding costs. Banks have benefited from structural reforms and resilient credit demand from customers in retail, SME and corporate segments. In BoM, improved yield realization and prudent asset-liability management contributed to a healthier NII line, even as risk controls remained in focus.</P><H3>Asset quality and risk metrics</H3><P>Asset quality improved in the quarter with lower gross NPAs and a reduction in net NPAs, an important signal for investors watching credit discipline. Lower stress indicators reduce provisioning pressures and support a more stable earnings profile. The bank\u2019s impairment charges are expected to ease, contributing to more predictable quarterly results going forward.</P><H2>Implications for investors</H2><P>From an investment perspective, the Q4 results signal that Bank of Maharashtra is on a path of sustainable profitability driven by core banking activities rather than one-off income. Retail and SME credit demand continues to show resilience, while the bank's CASA base is encouraging for funding costs. For global investors, stable earnings growth in a domestic financial institution aligns with the broader trend of Indian banks expanding market share and improving efficiency year after year.</P><H3>Portfolio implications</H3><P>Investors evaluating Indian banks should consider a mix of public sector lenders and private players to balance risk and growth. BoMs improving efficiency and disciplined credit cost could make it a viable candidate for value-oriented investors seeking steady dividend yield and long-term capital appreciation. It is important to review quarterly commentary, management guidance, and regulatory developments from SEBI in order to align with risk tolerance and investment horizon.</P><H2>How to approach BoM within your personal investing journey</H2><P>For new investors, understanding bank earnings requires context around the regulatory framework, including SEBI guidelines, disclosure norms, and reporting standards. Opening a demat account with a registered broker is the first step to participate in Indian equities, with platforms such as Zerodha Groww Angel One Upstox and ICICI Direct offering education tools to help beginners. These brokers provide research reports, stock screeners, and educational content that complements your own study of BoM results. Swastika Investmart is highlighted here for its trusted research, compliant advisory, and investor-friendly guidance, which can help a learner translate quarterly results into actionable investment ideas.</P><H3>Practical steps for beginners</H3><P>1) Start with a free stock market account and learn how to interpret financial statements. 2) Review quarterly press releases and investor presentations for BoM. 3) Use risk-managed position sizing and a long term lens while tracking NII, deposits, and loan growth. 4) Keep demat accounts with a trusted broker and use research services from channels such as Swastika Investmart to build confidence. 5) Follow SEBI regulations and ensure you understand corporate actions and dividend announcements to plan your investments.</P><H2>Industry context and regulatory landscape</H2><P>Indian banks operate under a robust regulatory regime governed by SEBI and the Reserve Bank of India RBI. Public sector lenders like Bank of Maharashtra must adhere to capital adequacy norms, provisioning standards, and disclosure requirements that give retail investors a clearer view of risk and return. The adoption of standardized reporting helps investors compare BoM with peers in the sector. A growing number of investors are opening demat accounts, subscribing to equity mutual funds, and using online brokers to build diversified portfolios with exposure to financials, information technology, and other growth sectors.</P><H2>Swastika Investmart and investor education</H2><P>Swastika Investmart is presented here as a trusted partner for research, compliance, and advisory services. A focus on transparent research methodologies, adherence to regulatory standards, and a commitment to investor education helps beginners gain confidence in their analyses. By combining independent research with broker platforms such as Zerodha Groww Angel One Upstox ICICI Direct and a clear investor journey, beginners can make more informed choices about which stocks to consider and how to structure their first investments with a long term horizon.</P><H2>Conclusion</H2><P>Bank of Maharashtra Q4 results highlight a positive shift in profitability driven by NII growth and an improving asset quality framework. The blend of higher loan growth, prudent risk management, and continued emphasis on core banking operations positions BoM as a participant worth watching in the Indian banking space. For retail investors, these results reinforce the value of building knowledge through credible research, using demat accounts, and engaging with experienced advisory services. The Indian market offers opportunities across public sector lenders and private banks, and a disciplined approach to learning, supported by trusted platforms like Swastika Investmart, can help beginners translate quarterly performance into a sound investment plan that aligns with long term goals.</P>
    Output: 
        blog_notify: "Bank of Maharastra ka net profit bada 34% se, swastika app se trade kare Bank of maharsthra aur apna bhi profit bdaye!!."
"""

    result = cached_model_call(prompt)
      # Convert string → JSON
    data = json.loads(result)

    return data