"""
Viral Content Factory for Personal Trainers
Generates engaging social media content designed to go viral
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class ViralContentFactory:
    """
    Factory class for generating viral social media content for personal trainers.
    Creates engaging posts that drive engagement, build community, and attract clients.
    """
    
    def __init__(self):
        """Initialize the ViralContentFactory with content templates and data."""
        self.metrics_templates = [
            "lost {weight} pounds",
            "gained {muscle} pounds of muscle",
            "increased strength by {percentage}%",
            "reduced body fat by {percentage}%",
            "improved endurance by {time}",
            "squatted {weight} pounds",
            "deadlifted {weight} pounds",
            "bench pressed {weight} pounds"
        ]
        
        self.timeframes = [
            "in just 8 weeks",
            "in 3 months",
            "in 6 months",
            "in 1 year",
            "in 90 days",
            "in 12 weeks",
            "in 6 weeks",
            "in 4 months"
        ]
        
        self.social_proof_elements = [
            "Over 500+ trainers have used this method",
            "This approach has helped 1000+ clients",
            "Featured in major fitness publications",
            "Used by top 1% of trainers worldwide",
            "Backed by sports science research",
            "Recommended by industry experts",
            "Proven in 50+ gyms nationwide",
            "Trusted by professional athletes"
        ]
        
        self.myths = [
            "You need to work out 2+ hours daily to see results",
            "Cardio is the only way to lose weight",
            "You can spot-reduce fat in specific areas",
            "Lifting weights makes women bulky",
            "You need expensive supplements to build muscle",
            "More protein = more muscle automatically",
            "You can out-exercise a bad diet",
            "Rest days are optional for serious athletes"
        ]
        
        self.confession_templates = [
            "Confession: I'm a trainer and I still struggle with {struggle}",
            "Confession: I'm a trainer and I {secret}",
            "Confession: I'm a trainer and I wish I knew {wish}",
            "Confession: I'm a trainer and I {vulnerability}",
            "Confession: I'm a trainer and I {honest_truth}",
            "Confession: I'm a trainer and I {personal_story}"
        ]
        
        self.challenge_types = [
            "7-Day Client Communication Challenge",
            "30-Day Social Media Growth Challenge",
            "14-Day Nutrition Education Challenge",
            "21-Day Business Development Challenge",
            "10-Day Workout Programming Challenge",
            "28-Day Client Retention Challenge"
        ]

    def generate_before_after_post(self, transformation_story: Dict[str, str]) -> str:
        """
        Generate a dramatic before/after transformation post.
        
        Args:
            transformation_story: Dict containing client details, metrics, timeframe
            
        Returns:
            Formatted viral before/after post
        """
        client_name = transformation_story.get('name', 'Sarah')
        before_weight = transformation_story.get('before_weight', '180 lbs')
        after_weight = transformation_story.get('after_weight', '145 lbs')
        timeframe = transformation_story.get('timeframe', random.choice(self.timeframes))
        key_metric = transformation_story.get('key_metric', 'lost 35 pounds')
        struggle = transformation_story.get('struggle', 'struggled with emotional eating')
        breakthrough = transformation_story.get('breakthrough', 'discovered sustainable habits')
        
        social_proof = random.choice(self.social_proof_elements)
        
        post = f"""🔥 BEFORE & AFTER: {client_name}'s Transformation Story

BEFORE: {before_weight}, {struggle}
AFTER: {after_weight}, {breakthrough}

📊 THE NUMBERS:
• {key_metric} {timeframe}
• {random.choice(['No crash diets', 'No extreme restrictions', 'No unsustainable methods'])}
• {random.choice(['Sustainable lifestyle change', 'Long-term habit formation', 'Realistic approach'])}

💡 WHAT CHANGED:
Instead of {random.choice(['quick fixes', 'extreme measures', 'unsustainable diets'])}, we focused on:
✅ {random.choice(['Consistent habits', 'Small daily changes', 'Realistic goals'])}
✅ {random.choice(['Proper nutrition education', 'Sustainable exercise routine', 'Mindset shifts'])}
✅ {random.choice(['Long-term lifestyle changes', 'Habit stacking', 'Gradual progress'])}

🎯 THE RESULT:
{client_name} didn't just change her body - she changed her LIFE.

{social_proof}

Want to help YOUR clients achieve similar transformations? 
Drop a 💪 if you're ready to learn the exact system I used!

#TransformationTuesday #PersonalTrainer #FitnessSuccess #ClientResults #BeforeAndAfter #FitnessMotivation #TrainerLife #HealthJourney #SustainableFitness #RealResults"""

        return post

    def generate_myth_buster(self, misconception: str) -> str:
        """
        Generate authoritative myth-busting content.
        
        Args:
            misconception: The fitness/business myth to debunk
            
        Returns:
            Formatted myth-busting post
        """
        if not misconception:
            misconception = random.choice(self.myths)
        
        myth_busters = {
            "You need to work out 2+ hours daily to see results": {
                "truth": "45-60 minutes of focused training is optimal",
                "science": "Studies show diminishing returns after 60 minutes due to cortisol spikes",
                "alternative": "Focus on workout QUALITY over quantity. 45 minutes of high-intensity training beats 2 hours of half-hearted effort."
            },
            "Cardio is the only way to lose weight": {
                "truth": "Strength training + proper nutrition is more effective",
                "science": "Muscle burns 3x more calories at rest than fat tissue",
                "alternative": "Combine strength training 3x/week with moderate cardio for optimal fat loss."
            },
            "You can spot-reduce fat in specific areas": {
                "truth": "Fat loss happens systemically, not locally",
                "science": "Your body decides where to burn fat based on genetics and hormones",
                "alternative": "Focus on overall body fat reduction through consistent training and caloric deficit."
            },
            "Lifting weights makes women bulky": {
                "truth": "Women lack sufficient testosterone to build bulky muscle",
                "science": "Women have 10-20x less testosterone than men naturally",
                "alternative": "Strength training creates a lean, toned physique - not bulk."
            }
        }
        
        if misconception not in myth_busters:
            myth_busters[misconception] = {
                "truth": "This is a common misconception in the fitness industry",
                "science": "Research consistently shows this approach is ineffective",
                "alternative": "Focus on evidence-based methods that actually work."
            }
        
        myth_data = myth_busters[misconception]
        
        post = f"""🚨 MYTH BUSTED: "{misconception}"

❌ THE MYTH:
{misconception}

✅ THE TRUTH:
{myth_data['truth']}

🔬 THE SCIENCE:
{myth_data['science']}

💡 WHAT TO DO INSTEAD:
{myth_data['alternative']}

🎯 WHY THIS MATTERS:
Following myths like this keeps you stuck in the same place, wasting time and energy on approaches that don't work.

As trainers, it's our job to educate clients with FACTS, not fitness fiction.

What's the biggest fitness myth you've had to debunk with clients? 
Drop it below! 👇

#MythBusted #FitnessFacts #PersonalTrainer #EvidenceBased #FitnessEducation #TrainerLife #ScienceBased #FitnessMyths #HealthEducation #TrainerTips"""

        return post

    def generate_confession_post(self, confession_type: str = None) -> str:
        """
        Generate a vulnerable confession post that makes trainers feel seen.
        
        Args:
            confession_type: Type of confession (optional)
            
        Returns:
            Formatted confession post
        """
        confessions = {
            "imposter_syndrome": {
                "struggle": "imposter syndrome every single day",
                "secret": "sometimes doubt if I'm really helping my clients",
                "wish": "this feeling of not being 'good enough' would go away",
                "vulnerability": "still feel like I'm learning every single day",
                "honest_truth": "don't have all the answers, and that's okay",
                "personal_story": "started this journey feeling completely unqualified"
            },
            "client_challenges": {
                "struggle": "clients who don't follow through with their programs",
                "secret": "take it personally when clients don't show up",
                "wish": "I could make everyone's transformation journey easier",
                "vulnerability": "sometimes feel like I'm failing my clients",
                "honest_truth": "can't want it more than they do",
                "personal_story": "learned that I can't control client outcomes, only my effort"
            },
            "business_struggles": {
                "struggle": "pricing my services appropriately",
                "secret": "sometimes undercharge because I'm afraid of rejection",
                "wish": "I had learned business skills alongside fitness knowledge",
                "vulnerability": "still figuring out how to run a successful training business",
                "honest_truth": "love training but hate the business side",
                "personal_story": "started with zero business knowledge and learned through trial and error"
            },
            "work_life_balance": {
                "struggle": "maintaining my own fitness routine while training others",
                "secret": "sometimes skip my own workouts to train clients",
                "wish": "I could practice what I preach more consistently",
                "vulnerability": "feel guilty when I don't follow my own advice",
                "honest_truth": "helping others is easier than helping myself",
                "personal_story": "realized I need to prioritize my own health to serve others better"
            }
        }
        
        if not confession_type or confession_type not in confessions:
            confession_type = random.choice(list(confessions.keys()))
        
        confession_data = confessions[confession_type]
        template = random.choice(self.confession_templates)
        
        confession_text = template.format(**confession_data)
        
        post = f"""{confession_text}

But here's what I've learned:

💡 It's okay to not have all the answers
💡 Growth happens outside your comfort zone  
💡 Every trainer faces these same challenges
💡 Vulnerability creates deeper connections
💡 Progress > perfection, always

The truth is, being a trainer isn't just about knowing exercises and nutrition. It's about:
• Constantly learning and growing
• Being vulnerable with your clients
• Admitting when you don't know something
• Showing up even when you feel inadequate
• Learning from every client interaction

If you're reading this and nodding along, know that you're not alone. Every successful trainer has felt this way.

What's your biggest trainer confession? 
Let's normalize the struggle and celebrate the growth together! 🙌

#TrainerConfession #PersonalTrainer #Vulnerability #TrainerLife #FitnessCommunity #Authenticity #Growth #TrainerStruggles #RealTalk #FitnessIndustry"""

        return post

    def generate_challenge_post(self, challenge_type: str = None, duration: int = None) -> str:
        """
        Generate a community-building challenge post.
        
        Args:
            challenge_type: Type of challenge (optional)
            duration: Duration in days (optional)
            
        Returns:
            Formatted challenge post
        """
        if not challenge_type:
            challenge_type = random.choice(self.challenge_types)
        
        if not duration:
            duration = 7 if "7-Day" in challenge_type else 30 if "30-Day" in challenge_type else 14
        
        challenge_steps = {
            "7-Day Client Communication Challenge": [
                "Day 1: Send a check-in message to 5 clients",
                "Day 2: Ask one client about their biggest struggle",
                "Day 3: Share a motivational quote with your clients",
                "Day 4: Send a form asking for feedback on your services",
                "Day 5: Call one client to discuss their progress",
                "Day 6: Share a client success story (with permission)",
                "Day 7: Plan next week's communication strategy"
            ],
            "30-Day Social Media Growth Challenge": [
                "Week 1: Post daily with consistent branding",
                "Week 2: Engage with 20+ accounts daily",
                "Week 3: Share 3 client success stories",
                "Week 4: Create 5 educational carousel posts"
            ],
            "14-Day Nutrition Education Challenge": [
                "Days 1-3: Learn about macronutrients",
                "Days 4-7: Study portion control methods",
                "Days 8-10: Research meal timing strategies",
                "Days 11-14: Create nutrition handouts for clients"
            ]
        }
        
        if challenge_type not in challenge_steps:
            challenge_steps[challenge_type] = [
                f"Day {i+1}: Complete daily challenge task" for i in range(duration)
            ]
        
        steps = challenge_steps[challenge_type]
        
        hashtag = f"#{challenge_type.replace(' ', '').replace('-', '')}Challenge"
        
        post = f"""🎯 {challenge_type.upper()}

Ready to level up your trainer game? 

I'm launching a {duration}-day challenge that will transform how you {challenge_type.split(' ')[-1].lower()}!

📋 THE CHALLENGE:
{chr(10).join([f"• {step}" for step in steps[:min(7, len(steps))]])}

{'• ...and more daily tasks!' if len(steps) > 7 else ''}

🏆 WHAT YOU'LL GET:
✅ Daily actionable steps
✅ Community support from fellow trainers
✅ Accountability partners
✅ Exclusive resources and templates
✅ Certificate of completion

🎯 WHO THIS IS FOR:
• Personal trainers ready to level up
• Fitness professionals wanting to grow
• Anyone serious about improving their skills
• Trainers who thrive on community support

📅 STARTS: {datetime.now().strftime('%B %d, %Y')}
⏰ DURATION: {duration} days
📍 WHERE: Right here in the comments!

HOW TO JOIN:
1. Comment "I'M IN" below
2. Share this post to your story
3. Use the hashtag {hashtag}
4. Tag 3 trainer friends who need this!

The challenge starts NOW! 

Who's ready to transform their trainer business in just {duration} days? 

Drop your "I'M IN" below and let's do this together! 💪

{hashtag} #TrainerChallenge #FitnessCommunity #PersonalTrainer #GrowthChallenge #TrainerLife #FitnessEducation #CommunityChallenge #LevelUp #TrainerGoals #FitnessIndustry"""

        return post

    def generate_carousel_masterclass(self, topic: str, refiloe_link: str = "https://refiloe.com") -> str:
        """
        Generate a 10-slide educational carousel post.
        
        Args:
            topic: The masterclass topic
            refiloe_link: Link to Refiloe platform
            
        Returns:
            Formatted carousel post with slide descriptions
        """
        carousel_topics = {
            "Client Retention": {
                "hook": "Why 80% of trainers lose clients in 3 months (and how to keep them forever)",
                "slides": [
                    "The #1 reason clients quit (it's not what you think)",
                    "The 3-2-1 follow-up system that keeps clients engaged",
                    "How to create 'sticky' relationships with clients",
                    "The retention formula: Value + Connection + Results",
                    "5 red flags that predict client departure",
                    "The re-engagement strategy for at-risk clients",
                    "Building a client community that keeps them coming back"
                ],
                "recap": "Client retention = Consistent value + Genuine connection + Measurable results",
                "cta": "Ready to keep every client? Get the complete retention system at Refiloe!"
            },
            "Pricing Strategy": {
                "hook": "How to price your training services so clients say YES (and you make 6-figures)",
                "slides": [
                    "The psychology behind pricing (why cheap = low value)",
                    "3 pricing models that maximize your income",
                    "How to justify premium pricing to any client",
                    "The 'value ladder' that increases average sale",
                    "Pricing psychology: Anchoring, bundling, and scarcity",
                    "How to handle price objections like a pro",
                    "Creating packages that sell themselves"
                ],
                "recap": "Right pricing = Right positioning + Clear value + Confident delivery",
                "cta": "Master the art of premium pricing with our complete pricing course!"
            },
            "Social Media Growth": {
                "hook": "From 0 to 10K followers: The trainer's guide to viral social media",
                "slides": [
                    "The content pillars that guarantee engagement",
                    "Why 80% of trainer content gets ignored (and how to fix it)",
                    "The posting schedule that maximizes reach",
                    "Hashtag strategy that gets you discovered",
                    "How to turn followers into paying clients",
                    "The engagement tactics that build community",
                    "Creating content that educates AND entertains"
                ],
                "recap": "Social media success = Consistent value + Authentic engagement + Strategic growth",
                "cta": "Get the complete social media blueprint for trainers!"
            }
        }
        
        if topic not in carousel_topics:
            carousel_topics[topic] = {
                "hook": f"The complete guide to {topic} for personal trainers",
                "slides": [
                    f"Understanding {topic} fundamentals",
                    f"The biggest mistakes trainers make with {topic}",
                    f"Step-by-step {topic} implementation",
                    f"Advanced {topic} strategies",
                    f"Common {topic} challenges and solutions",
                    f"Measuring {topic} success",
                    f"Scaling your {topic} approach"
                ],
                "recap": f"Master {topic} with consistent application and continuous improvement",
                "cta": f"Get the complete {topic} system for trainers!"
            }
        
        content = carousel_topics[topic]
        
        post = f"""📚 MASTERCLASS: {topic.upper()}

{content['hook']}

Swipe through this 10-slide masterclass to learn everything you need to know! 👆

📖 SLIDE BREAKDOWN:

🎯 SLIDE 1: {content['hook']}

📋 SLIDES 2-8: The Complete System
{chr(10).join([f"• {slide}" for slide in content['slides']])}

🎯 SLIDE 9: {content['recap']}

🚀 SLIDE 10: {content['cta']}

💡 WHY THIS MATTERS:
Most trainers struggle with {topic.lower()} because they don't have a proven system. This masterclass gives you the exact framework used by top 1% trainers.

🎯 WHO THIS IS FOR:
• Personal trainers ready to level up
• Fitness professionals wanting to improve
• Anyone serious about {topic.lower()}
• Trainers who want proven strategies

📱 SAVE THIS POST:
Bookmark this for future reference and share with your trainer friends!

🔗 GET THE COMPLETE SYSTEM:
Ready to implement everything you learned? Get the full course, templates, and resources at Refiloe!

{refiloe_link}

What's your biggest challenge with {topic.lower()}? 
Drop it in the comments and I'll help you solve it! 👇

#Masterclass #PersonalTrainer #FitnessEducation #TrainerTips #FitnessIndustry #ProfessionalDevelopment #TrainerLife #FitnessBusiness #Education #Growth #Refiloe"""

        return post

    def generate_content_calendar(self, days: int = 7) -> Dict[str, str]:
        """
        Generate a week's worth of viral content.
        
        Args:
            days: Number of days to generate content for
            
        Returns:
            Dictionary with daily content suggestions
        """
        content_types = [
            "before_after_post",
            "myth_buster", 
            "confession_post",
            "challenge_post",
            "carousel_masterclass"
        ]
        
        calendar = {}
        for i in range(days):
            date = datetime.now() + timedelta(days=i)
            content_type = content_types[i % len(content_types)]
            
            if content_type == "before_after_post":
                calendar[date.strftime("%Y-%m-%d")] = self.generate_before_after_post({
                    'name': 'Client',
                    'before_weight': '180 lbs',
                    'after_weight': '145 lbs',
                    'timeframe': random.choice(self.timeframes),
                    'key_metric': 'lost 35 pounds'
                })
            elif content_type == "myth_buster":
                calendar[date.strftime("%Y-%m-%d")] = self.generate_myth_buster(random.choice(self.myths))
            elif content_type == "confession_post":
                calendar[date.strftime("%Y-%m-%d")] = self.generate_confession_post()
            elif content_type == "challenge_post":
                calendar[date.strftime("%Y-%m-%d")] = self.generate_challenge_post()
            elif content_type == "carousel_masterclass":
                calendar[date.strftime("%Y-%m-%d")] = self.generate_carousel_masterclass("Client Retention")
        
        return calendar


# Example usage and testing
if __name__ == "__main__":
    factory = ViralContentFactory()
    
    # Test each method
    print("=== BEFORE/AFTER POST ===")
    print(factory.generate_before_after_post({
        'name': 'Sarah',
        'before_weight': '180 lbs',
        'after_weight': '145 lbs',
        'timeframe': 'in 12 weeks',
        'key_metric': 'lost 35 pounds'
    }))
    
    print("\n=== MYTH BUSTER ===")
    print(factory.generate_myth_buster("You need to work out 2+ hours daily to see results"))
    
    print("\n=== CONFESSION POST ===")
    print(factory.generate_confession_post("imposter_syndrome"))
    
    print("\n=== CHALLENGE POST ===")
    print(factory.generate_challenge_post("7-Day Client Communication Challenge"))
    
    print("\n=== CAROUSEL MASTERCLASS ===")
    print(factory.generate_carousel_masterclass("Client Retention"))