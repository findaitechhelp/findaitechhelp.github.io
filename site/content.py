"""Original process guidance, distinct from evidence-backed directory records."""
STATES = dict(p.split(':',1) for p in ('al:Alabama|ak:Alaska|az:Arizona|ar:Arkansas|ca:California|co:Colorado|ct:Connecticut|de:Delaware|fl:Florida|ga:Georgia|hi:Hawaii|id:Idaho|il:Illinois|in:Indiana|ia:Iowa|ks:Kansas|ky:Kentucky|la:Louisiana|me:Maine|md:Maryland|ma:Massachusetts|mi:Michigan|mn:Minnesota|ms:Mississippi|mo:Missouri|mt:Montana|ne:Nebraska|nv:Nevada|nh:New Hampshire|nj:New Jersey|nm:New Mexico|ny:New York|nc:North Carolina|nd:North Dakota|oh:Ohio|ok:Oklahoma|or:Oregon|pa:Pennsylvania|ri:Rhode Island|sc:South Carolina|sd:South Dakota|tn:Tennessee|tx:Texas|ut:Utah|vt:Vermont|va:Virginia|wa:Washington|wv:West Virginia|wi:Wisconsin|wy:Wyoming').split('|'))
QUESTIONS = ['What will I learn or receive, and how will we check that it works?', 'What is the total price, including subscriptions and follow-up?', 'Can you show a relevant example without exposing another customer’s information?', 'Will I own the accounts, files, and work when the project ends?', 'What information do you need, and how will you protect it?']
AUDIENCES = {
 'individual': ('For yourself', 'Choose a task you care about, use your own pace, and ask for explanations in plain English.'),
 'business': ('For your small business', 'Pick a task you repeat and use sample data. Decide who will own the tool and teach the rest of the team.'),
 'team': ('For your team', 'Choose a project owner, use approved tools, and agree how staff will check results before using them with customers.'),
 'senior': ('For a family member or senior', 'Ask for plain language, larger text, and time to practice. Invite a trusted person if you want support. Keep control of your accounts and passwords.')
}
NEEDS = {
 'learn': {
  'label':'Learn to use AI','heading':'Start with one thing you’d like to do.',
  'summary':'Choose one ordinary task, practice with information you can safely share, and look for a class that matches your starting point.',
  'steps':[
   ('Choose a useful exercise','Try drafting a simple email, organizing a non-sensitive list, or asking for an explanation. Check the answer yourself before using it.'),
   ('Ask about free local learning','Contact your public library or a community education office. Ask about beginner AI classes, eligibility, accessibility, and device requirements.'),
   ('Compare before paying','Request the syllabus, level, format, and full price. Choose practical learning where you can ask questions and leave with something useful.')],
  'cost':'Ask about free options first. Get the current total price directly from the organizer; do not assume a free introduction includes a free certificate.',
  'safety':'Use made-up examples while learning. Keep passwords, customer information, and private documents out of practice prompts.',
  'guide':'choose-ai-training'
 },
 'setup': {
  'label':'Get something set up','heading':'Make the first project small and clear.',
  'summary':'Describe the task before choosing a tool. A small project with a clear result is easier to price, test, and hand over.',
  'steps':[
   ('Write down the job','Describe what happens now, what is repetitive, and what a better result looks like. Use sample information instead of private records.'),
   ('Check what you already use','Ask your current IT or software provider whether the task is supported. Discuss setup, subscriptions, ownership, and maintenance.'),
   ('Request a written first step','Ask for a small scope, clear deliverables, a test you can observe, and a handover plan. Compare proposals before committing.')],
  'cost':'Request a quote separating setup, recurring subscriptions, training, and support. Ask what happens when requirements change.',
  'safety':'Keep ownership of accounts. Use permission-based access rather than sharing passwords, and agree how to remove access afterward.',
  'guide':'plan-an-ai-project'
 },
 'repair': {
  'label':'Fix my technology','heading':'Protect your files. Then explain the problem.',
  'summary':'A clear description helps a repair shop or IT service understand the job. Don’t install a repair tool or give remote access because a pop-up told you to.',
  'steps':[
   ('Write down what changed','Note the device, error message, and when the problem started. If there is smoke, heat, swelling, or a liquid spill, stop using the device and seek qualified help.'),
   ('Protect your information','If it is safe to do so, check that you have a backup. Avoid a factory reset or unfamiliar cleanup software before understanding what could be lost.'),
   ('Ask about diagnosis','Contact a repair service yourself. Ask about diagnostic fees, estimates before work begins, data handling, and what happens if repair is not possible.')],
  'cost':'Ask whether diagnosis is charged, whether it counts toward repair, and whether you must approve extra work. Get an estimate in writing.',
  'safety':'Treat unsolicited remote-support requests and urgent payment demands as warning signs. Contact the service through details you found independently.',
  'guide':'computer-help-without-the-pressure'
 },
 'unsure': {
  'label':'I’m not sure yet','heading':'Start with the problem, not the technology.',
  'summary':'You don’t have to choose a product today. Write down one thing you want to understand or improve, then choose a small, safe next step.',
  'steps':[
   ('Name the friction','Is a task taking too long, is a tool confusing, or is a device not working? Describe the situation in ordinary words.'),
   ('Choose the type of help','Start with learning for confidence, a small setup project for a repeatable task, or repair when basic technology is failing.'),
   ('Take one reversible step','Ask a question, try a safe practice exercise, or get a written estimate. Avoid subscriptions and large commitments until you understand the outcome.')],
  'cost':'Prepare your questions before spending. Ask for the full price and an explanation of alternatives.',
  'safety':'A helpful professional can explain the work without pressure, guaranteed-result claims, or a demand for your passwords.',
  'guide':'five-questions-before-you-hire'
 }
}
GUIDES = {
 'choose-ai-training': {'title':'How to choose an AI class you can actually use','tag':'Learning','description':'Compare formats, starting levels, and full costs before enrolling.','need':'learn'},
 'plan-an-ai-project': {'title':'Plan a small AI project before hiring anyone','tag':'Getting set up','description':'Turn a vague automation idea into a clear scope, test, and handover.','need':'setup'},
 'computer-help-without-the-pressure': {'title':'Get computer help without the pressure','tag':'Everyday technology','description':'Prepare for a repair conversation and keep control of your files and accounts.','need':'repair'},
 'five-questions-before-you-hire': {'title':'Five questions before hiring AI or tech help','tag':'Making a decision','description':'A checklist for the result, price, ownership, privacy, and follow-up.','need':'unsure'}
}
