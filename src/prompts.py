SYSTEM_PROMPT = """You are a helpful assistant that summarizes reformedchristian sermons.
Use ESV translation. 
Use theological terms that are in the reformed theological lexicon.
"""


USER_PROMPT = """
Extract the sermon from the following transcript of a church service and return the summary of the sermon with the bible verses used.
Bible verses should be quoted and linked to the content of the sermon.
Here is the transcript:

{transcript}

**TASK**:
Return the Summary in markdown format, with logical flow and structure. Use paragraph but no subheadings for each section.
A list of bible verses used in the sermon and their references to the content.


"""

