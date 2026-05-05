# SEO  
  
**what i built**  
the system runs inside Claude Cowork. before i run any prompt, i give Claude everything it needs to work from real data instead of guesses:  
* a folder with my business name, address, phone number, website, GBP URL, service areas, and target keywords - loaded once, never repeated  
* a file for every competitor with their GBP URLs so every audit runs comparisons automatically  
* my Google Business Profile details uploaded so Claude knows my current categories, attributes, photos, and services before i ask anything  
* a prompt library - one file per SEO task - so every prompt already knows my business when i paste it in  
that setup is what separates a tool from a system. without it, Claude gives you generic output. with it, every prompt feels like it was written specifically for your business. because it was.  
**the prompt stack**  
**the prompt stack**  
**1. GBP category audit**  
**1. GBP category audit**  
this is where i start with every single client. because if your categories are wrong, nothing else matters.  
your GBP has a primary category and secondary categories. most business owners picked their primary category when they created their listing years ago and never touched it again. meanwhile competitors have added secondary categories they didn't know existed - and those categories directly control which searches trigger your listing in the map pack.  
your GBP has a primary category and secondary categories. most business owners picked their primary category when they created their listing years ago and never touched it again. meanwhile competitors have added secondary categories they didn't know existed - and those categories directly control which searches trigger your listing in the map pack.  
wrong categories = invisible for high-intent searches. it's that simple.  
wrong categories = invisible for high-intent searches. it's that simple.  
the prompt:  
the prompt:  
*"Open Chrome and go to Google Maps. Search '[service] in [city]' for these 3 keywords: [keyword1], [keyword2], [keyword3]. For each search, note which of my competitors show up in the Map Pack. Then open each competitor's GBP listing and extract their primary category and all secondary categories. Put everything in a spreadsheet. One tab per keyword. Columns: business name, primary category, secondary categories, star rating, review count, ranking position. Highlight any categories my competitors have that I'm missing from my GBP."*  
*"Open Chrome and go to Google Maps. Search '[service] in [city]' for these 3 keywords: [keyword1], [keyword2], [keyword3]. For each search, note which of my competitors show up in the Map Pack. Then open each competitor's GBP listing and extract their primary category and all secondary categories. Put everything in a spreadsheet. One tab per keyword. Columns: business name, primary category, secondary categories, star rating, review count, ranking position. Highlight any categories my competitors have that I'm missing from my GBP."*  
why this matters:  
why this matters:  
i've had clients add one secondary category and start showing up for a whole new set of searches the next week. fastest win in local SEO.  
but the real power is pattern recognition. when you map categories against map pack rankings you start seeing things. like every business ranking for "emergency plumber in [city]" also has "water damage restoration" as a secondary category. those patterns are invisible unless you do this analysis. Claude does the gathering. you do the thinking.  
but the real power is pattern recognition. when you map categories against map pack rankings you start seeing things. like every business ranking for "emergency plumber in [city]" also has "water damage restoration" as a secondary category. those patterns are invisible unless you do this analysis. Claude does the gathering. you do the thinking.  
**2. GBP attributes audit**  
this one flies under the radar. most people don't even know GBP attributes exist - let alone that they affect rankings and conversions.  
attributes are the little tags on your profile. "veteran-owned." "free estimates." "24/7 availability." "accepts credit cards." Google uses these to match searchers with businesses. someone searches "24 hour plumber near me" - Google looks at which GBP listings have the 24/7 attribute. someone searches "woman-owned cleaning company" - same thing.  
attributes are the little tags on your profile. "veteran-owned." "free estimates." "24/7 availability." "accepts credit cards." Google uses these to match searchers with businesses. someone searches "24 hour plumber near me" - Google looks at which GBP listings have the 24/7 attribute. someone searches "woman-owned cleaning company" - same thing.  
your competitors have attributes you don't. guaranteed.  
your competitors have attributes you don't. guaranteed.  
the prompt:  
*"Open Chrome and go to my Google Business Profile at [URL] and these competitors: [URL1], [URL2], [URL3]. For each listing, extract every visible attribute and tag -things like 'veteran-owned,' 'free estimates,' 'offers online appointments,' 'wheelchair accessible,' '24/7 availability,' and any others shown. Put everything in a spreadsheet. Columns: attribute name, my listing (yes/no), competitor 1 (yes/no), competitor 2 (yes/no), competitor 3 (yes/no). Highlight every attribute my competitors have that I'm missing. Then list any attributes that ALL top competitors share - those are the baseline requirements for ranking in this market."*  
*"Open Chrome and go to my Google Business Profile at [URL] and these competitors: [URL1], [URL2], [URL3]. For each listing, extract every visible attribute and tag -things like 'veteran-owned,' 'free estimates,' 'offers online appointments,' 'wheelchair accessible,' '24/7 availability,' and any others shown. Put everything in a spreadsheet. Columns: attribute name, my listing (yes/no), competitor 1 (yes/no), competitor 2 (yes/no), competitor 3 (yes/no). Highlight every attribute my competitors have that I'm missing. Then list any attributes that ALL top competitors share - those are the baseline requirements for ranking in this market."*  
why this matters:  
why this matters:  
attributes are a two-for-one play. they help you rank for more specific searches AND they increase click-through rate because those little tags build trust before someone even clicks your listing.  
attributes are a two-for-one play. they help you rank for more specific searches AND they increase click-through rate because those little tags build trust before someone even clicks your listing.  
the "baseline requirements" part is the key insight. if all three top competitors have "free estimates" and you don't - that's not optional. that's table stakes. this audit shows you what's expected in your market versus what's a differentiator.  
the "baseline requirements" part is the key insight. if all three top competitors have "free estimates" and you don't - that's not optional. that's table stakes. this audit shows you what's expected in your market versus what's a differentiator.  
**3. competitor review teardown**  
reviews are the most visible ranking factor in local SEO. but most business owners look at their competitor's star rating and stop there.  
reviews are the most visible ranking factor in local SEO. but most business owners look at their competitor's star rating and stop there.  
star rating tells you almost nothing. what actually matters is review velocity - how fast they're getting new reviews compared to you. a business with 200 reviews that got 180 of them two years ago is weaker than a business with 90 reviews getting 15 a month. Google tracks this. you should too.  
star rating tells you almost nothing. what actually matters is review velocity - how fast they're getting new reviews compared to you. a business with 200 reviews that got 180 of them two years ago is weaker than a business with 90 reviews getting 15 a month. Google tracks this. you should too.  
the prompt:  
the prompt:  
*"Open Chrome and go to these competitor GBP listings: [URL1], [URL2], [URL3]. For each competitor, read their last 50 reviews. Extract: total review count, average rating, how many reviews in the last 30/60/90 days, the most mentioned services in reviews, the most mentioned neighborhoods or cities, and any recurring complaints. Then compare their review velocity to mine at [my GBP URL]. Output a spreadsheet with all this data and a separate tab that says exactly how many reviews per month I need to catch the top competitor and how long it will take."*  
*"Open Chrome and go to these competitor GBP listings: [URL1], [URL2], [URL3]. For each competitor, read their last 50 reviews. Extract: total review count, average rating, how many reviews in the last 30/60/90 days, the most mentioned services in reviews, the most mentioned neighborhoods or cities, and any recurring complaints. Then compare their review velocity to mine at [my GBP URL]. Output a spreadsheet with all this data and a separate tab that says exactly how many reviews per month I need to catch the top competitor and how long it will take."*  
why this matters:  
why this matters:  
that second tab is your entire review strategy for the next 6-12 months. you'll know exactly how many reviews per month you need.  
but here's the deeper insight - look at what customers mention in reviews. the services they name. the neighborhoods they reference. "great furnace install in highland park" is doing SEO work for that competitor whether they know it or not. reviews with keywords and location names are ranking signals. this data tells you exactly what to ask your happy customers to mention.  
but here's the deeper insight - look at what customers mention in reviews. the services they name. the neighborhoods they reference. "great furnace install in highland park" is doing SEO work for that competitor whether they know it or not. reviews with keywords and location names are ranking signals. this data tells you exactly what to ask your happy customers to mention.  
**4. review response strategy**  
**4. review response strategy**  
getting reviews is half the battle. how you respond is the other half.  
Google has confirmed that responding to reviews improves local ranking. but most businesses either don't respond at all or paste the same "thanks for your review!" on everything.  
your review responses are free real estate for keywords and service mentions. and how you handle negative reviews directly influences whether new customers trust you or scroll past.  
your review responses are free real estate for keywords and service mentions. and how you handle negative reviews directly influences whether new customers trust you or scroll past.  
the prompt:  
the prompt:  
*"Open Chrome and go to my GBP listing at [URL] and these competitors: [URL1], [URL2], [URL3]. For each listing, analyze the last 30 review responses from the business owner. Note: how many reviews have responses vs no response, average response time, whether responses mention specific services or locations, response length and tone, and how negative reviews are handled. Put this in a spreadsheet comparing my response strategy vs competitors. Then write me a review response template system: one template for 5-star reviews that naturally includes service + location keywords, one for 4-star reviews, one for 3-star reviews, and one for 1-2 star reviews that's professional and defuses negativity. Each template should have 3 variations so my responses don't look robotic."*  
*"Open Chrome and go to my GBP listing at [URL] and these competitors: [URL1], [URL2], [URL3]. For each listing, analyze the last 30 review responses from the business owner. Note: how many reviews have responses vs no response, average response time, whether responses mention specific services or locations, response length and tone, and how negative reviews are handled. Put this in a spreadsheet comparing my response strategy vs competitors. Then write me a review response template system: one template for 5-star reviews that naturally includes service + location keywords, one for 4-star reviews, one for 3-star reviews, and one for 1-2 star reviews that's professional and defuses negativity. Each template should have 3 variations so my responses don't look robotic."*  
why this matters:  
the template system is the real value here. most businesses struggle with reviews because every response feels like it takes 10 minutes to write. with templates and variations, you respond to any review in under a minute.  
the template system is the real value here. most businesses struggle with reviews because every response feels like it takes 10 minutes to write. with templates and variations, you respond to any review in under a minute.  
and those keyword-rich responses add up. 10 reviews a month, each response mentioning your service and city - that's 120 pieces of keyword-rich content on your GBP per year that you didn't have before.  
and those keyword-rich responses add up. 10 reviews a month, each response mentioning your service and city - that's 120 pieces of keyword-rich content on your GBP per year that you didn't have before.  
**5. GBP posts strategy**  
GBP posts are the most underused feature on the platform. most businesses don't even know they exist.  
posts show up directly on your listing. they expire after 7 days. and posting consistently signals to Google that your business is active. active businesses get preferred placement.  
posts show up directly on your listing. they expire after 7 days. and posting consistently signals to Google that your business is active. active businesses get preferred placement.  
your competitors probably aren't posting. that's your advantage right now.  
your competitors probably aren't posting. that's your advantage right now.  
the prompt:  
the prompt:  
*"Open Chrome and go to my GBP listing at [URL] and these competitors: [URL1], [URL2], [URL3]. For each listing, check their GBP posts section. Note: how many posts in the last 90 days, what type of posts, whether posts include images and CTAs, what topics they cover, and how often they post. Put this in a spreadsheet. Then build me an 8-week GBP posting calendar. I want 2-3 posts per week covering: seasonal service promotions, before-and-after project showcases, neighborhood-specific content mentioning areas we serve ([area1], [area2], [area3]), review highlights, and team spotlights. Each post should naturally include at least one target keyword from this list: [keyword1], [keyword2], [keyword3]. Write the first 4 weeks of posts for me - full copy and image suggestions."*  
*"Open Chrome and go to my GBP listing at [URL] and these competitors: [URL1], [URL2], [URL3]. For each listing, check their GBP posts section. Note: how many posts in the last 90 days, what type of posts, whether posts include images and CTAs, what topics they cover, and how often they post. Put this in a spreadsheet. Then build me an 8-week GBP posting calendar. I want 2-3 posts per week covering: seasonal service promotions, before-and-after project showcases, neighborhood-specific content mentioning areas we serve ([area1], [area2], [area3]), review highlights, and team spotlights. Each post should naturally include at least one target keyword from this list: [keyword1], [keyword2], [keyword3]. Write the first 4 weeks of posts for me - full copy and image suggestions."*  
why this matters:  
why this matters:  
the competitor analysis almost always reveals the same thing: nobody's posting. that means consistent posting immediately sets you apart.  
the competitor analysis almost always reveals the same thing: nobody's posting. that means consistent posting immediately sets you apart.  
but the real play is neighborhood-specific content. every time you publish a post mentioning "just completed a kitchen remodel in [neighborhood]" you're building location relevance. Google sees your business associated with that area. do this across 8-10 neighborhoods every month and you're building local authority that's extremely hard to replicate.  
but the real play is neighborhood-specific content. every time you publish a post mentioning "just completed a kitchen remodel in [neighborhood]" you're building location relevance. Google sees your business associated with that area. do this across 8-10 neighborhoods every month and you're building local authority that's extremely hard to replicate.  
**6. services section optimization**  
Google gives you an entire section to list your services with descriptions. this is prime keyword real estate and almost nobody optimizes it.  
most businesses leave it blank or add services with no descriptions. that's like having a landing page with just a title and no content. Google needs text to understand what you do and match you to searches.  
the prompt:  
the prompt:  
*"Open Chrome and go to my GBP listing at [URL] and these competitors: [URL1], [URL2], [URL3]. For each listing, check the services section. Extract: every service listed, whether it has a description, how detailed the descriptions are, and any service categories or groupings. Put this in a spreadsheet comparing my services section vs competitors. Then audit my current services section against my website [URL] and find any services on my site that aren't listed on my GBP. Finally, write optimized descriptions for all my services. Each description should be 2-3 sentences, naturally include target keywords, mention specific service areas where relevant, and include a benefit statement. Here are my core services: [service1], [service2], [service3] and service areas: [area1], [area2], [area3]."*  
*"Open Chrome and go to my GBP listing at [URL] and these competitors: [URL1], [URL2], [URL3]. For each listing, check the services section. Extract: every service listed, whether it has a description, how detailed the descriptions are, and any service categories or groupings. Put this in a spreadsheet comparing my services section vs competitors. Then audit my current services section against my website [URL] and find any services on my site that aren't listed on my GBP. Finally, write optimized descriptions for all my services. Each description should be 2-3 sentences, naturally include target keywords, mention specific service areas where relevant, and include a benefit statement. Here are my core services: [service1], [service2], [service3] and service areas: [area1], [area2], [area3]."*  
why this matters:  
your services section is one of the only places on your GBP where you control the text. reviews are written by customers. Q&A can come from anyone. but service descriptions? that's your copy. your keywords. your messaging.  
the cross-reference against your website catches a common mistake: businesses add new services to their site but forget to update their GBP. if you do "trenchless sewer repair" but it's not on your GBP, you're invisible for that search in the map pack.  
**7. GBP description optimization**  
**7. GBP description optimization**  
your GBP description is 750 characters of prime real estate. most businesses waste it.  
they either leave it blank, copy-paste from their website, or stuff it with keywords that sound robotic. your description needs to do three things: include your primary keywords naturally, mention your core service areas, and convince someone to choose you over the five other businesses on the screen.  
the prompt:  
the prompt:  
*"Open Chrome and go to my GBP listing at [URL] and these competitors: [URL1], [URL2], [URL3]. Extract each business's full GBP description. Put them in a spreadsheet with columns: business name, full description text, character count, keywords mentioned, service areas mentioned, unique selling points mentioned, and CTA included. Then analyze what top-ranking competitors emphasize vs what i'm saying. Identify the gaps. Finally, write me 3 versions of an optimized GBP description (max 750 characters each). Version 1: keyword-focused for maximum ranking signal. Version 2: conversion-focused for maximum calls. Version 3: balanced approach. All three must include these keywords: [keyword1], [keyword2], [keyword3] and these service areas: [area1], [area2], [area3]. Make them sound human, not robotic."*  
why this matters:  
why this matters:  
having 3 versions lets you test. run version 1 for 30 days. check impressions and calls. try version 2. most people write one description and forget about it forever. treating it as a testable asset gives you a compounding edge.  
**8. GBP photo audit**  
Google has said that businesses with photos get 42% more requests for directions and 35% more click-throughs. but it's not just about having photos - it's about the right photos uploaded consistently.  
most businesses uploaded 10 blurry phone pics three years ago and called it done. meanwhile the competitor dominating the map pack uploads weekly and has before-and-after shots that build trust before anyone even calls.  
the prompt:  
the prompt:  
*"Open Chrome and go to my GBP listing at [URL] and these competitors: [URL1], [URL2], [URL3]. For each listing, count: total photos, photos uploaded in the last 90 days, types of photos (team, jobs, before-after, office, trucks, equipment), and whether any look like stock photos. Put this in a spreadsheet comparing me vs each competitor. Then give me a specific 8-week photo upload plan for my GBP. Tell me exactly how many photos per week and what type to shoot. Focus on before-afters, team on job sites, trucks in neighborhoods we serve, and close-ups of completed installs. No generic office photos."*  
why this matters:  
why this matters:  
consistency beats volume. uploading 50 photos in one day then nothing for 6 months tells Google you're not active. uploading 3-5 quality photos every week tells Google your business is alive and thriving.  
consistency beats volume. uploading 50 photos in one day then nothing for 6 months tells Google you're not active. uploading 3-5 quality photos every week tells Google your business is alive and thriving.  
the type of photos matters. before-and-afters show competence. team photos build trust. trucks in specific neighborhoods signal service areas. the 8-week plan removes the guesswork entirely.  
**what stays human**  
this is the part most people get wrong.  
this is the part most people get wrong.  
Claude Cowork doesn't rank your business. you do.  
Claude Cowork doesn't rank your business. you do.  
what it does is eliminate every excuse you had for not doing this work. "i don't have time to analyze competitors." done. "i don't know what categories to add." done. "i don't know what to post." done.  
the strategy still requires a human brain. knowing which keywords actually bring in revenue. understanding your local market. reading between the lines of competitor data. figuring out that the reason your competitor ranks isn't their SEO - it's that they've been sponsoring little league teams for 10 years and have backlinks from every local news site in town.  
Claude does the research in minutes. you make the decisions that matter.  
Claude does the research in minutes. you make the decisions that matter.  
**how to use this**  
don't run all 8 at once. here's the order:  
don't run all 8 at once. here's the order:  
week 1 - fix the foundation: category audit and attributes audit. fastest fixes with the most immediate ranking impact. you could see changes within days.  
week 1 - fix the foundation: category audit and attributes audit. fastest fixes with the most immediate ranking impact. you could see changes within days.  
week 2 - optimize your listing: services section, description optimization. this fills your GBP with keyword-rich content Google can index.  
week 3 - review strategy: review teardown and response templates. now you have a velocity target and a system that turns every review into a ranking signal.  
week 4 - content engine: GBP posts calendar and photo audit. this gives you an ongoing content system that keeps your listing active and builds location relevance week after week.  
week 5 and beyond: execute. post consistently. upload photos weekly. respond to every review. this is where the compounding starts.  
90 days of consistent execution on this system and you will outrank businesses that have been established for years. i've watched it happen dozens of times.  
90 days of consistent execution on this system and you will outrank businesses that have been established for years. i've watched it happen dozens of times.  
**the real talk**  
**the real talk**  
90% of people reading this will save it and never run a single prompt. that's just how it goes.  
90% of people reading this will save it and never run a single prompt. that's just how it goes.  
if you want my team to run this entire system for your business - every audit, every optimization, every month of execution - that's what we do at Alventra Marketing.  
we've helped home services businesses generate hundreds of thousands in new revenue using this exact framework.  
we've helped home services businesses generate hundreds of thousands in new revenue using this exact framework.  
DM me if you want to talk about it. no pressure. but if you're serious about dominating your local market, the system works.  
DM me if you want to talk about it. no pressure. but if you're serious about dominating your local market, the system works.  
now stop reading and go run prompt 1.  
now stop reading and go run prompt 1.  
  
