Update:
- different size canvas is the future; people can mix and match
- pastel colors to begin with 
- on canvas -- done 
    - top; author, year of book
    - bottom: shapes of stories branding 
- need to:
    - refine logic for generating text; if outside acceptable range then quick so I can mannually adjust
    - refine logic for generate arc text 
    - refine logic for creating smoother curves without truncations 


Website:
- About
- Story Walls
    - with templates
- Shop/Explore 



update: 1/6/2024
- I have created a way to automatically create stories
- I think right now posters are causing me too much fuss and I just need to move forward
- going to go with 5x7 horizontal prints -- one per story and plan is to just make a ton 
- launch with basic background and fonts 
- need to figure out title placement 


# Things to do:
1. polish story creation prompt --> work with anthropic
2. schedule batches for story 
3. 




# Things to work on
1. Improve descriptors generation 
   - I think with each descriptor you need an explanation of the descriptor. 
   - If it's a character I think it should be when the character is introduced 
   - maybe you should only am for a couple descriptors in each segment 


2. Improve framwork prompt -- potentially add new arc types 

3. Dynamic Resizing of curves to fit descriptors 
   1. buffer of +5/-5 characters --> if outside buffer generate new descriptors 
   - if inside buffer modify end segment 
   - scale next segment x,y values 



Steps iterating across story_components:
1. calculate initial x,y values of story component arc --> use scaled start and end times and scaled start and end end_emotional_score
2. calculate length of story story component arc and the expected number of characters (X) of text that would fill up that arc
3. ask LLM to look at story component description to come up with consicse and succinct words or phrasses that range from (X+offset) - 5 to (X+offset) - 5 characters
4. calc the actual number of characters in LLM output 
5. update offset which is (actual number of characters in LLM output) - (X+offset); this is so that actual numbers of LLM outputs are not consistency too small or large vs target across story component 
6. create arc now with text from LLM output; if arc is now a little longer than previously expected that extrpolate teh section out; if arc is a little shorter than truncate
7. update next story component startin x,y values based off of new ending of story component at ahnd 
8. go to next story component and start steps over again  








0. calc arc 
1. get length
2. get targer num of chars --> update json with expected characters 
3. get proposed descriptors
    - Send to LLM saying you want to use these descriptors in range of (X+offset)-5 to (X+offset) +5 chars 
    - use existing context 
    - use these descriptors as a guide
4. check to see if new descriptors +/- X (5?) chars of target length
    - if no recalc 
    - if yes move on
5. calc updated offset which is number from expected 
6. calc section now with full chars
    - if new end is longer than expected than extropolate out
7. calc next step new starting x
7. recalc next section arc (i.e. go back to step 0)




Approach: 
1. Brute Force
    - brute force words to be in X chars of line
    - move segment x,y +/- 1 until all of text fits (more in json space) but can't surpas y_max y_min or x_max x_min 
2. Manual Inspection 


Approach:
1. Step by step testing 
2. curve arc



NEw Approach:
1. Calc length
2. calc expected chars/words
3. brute force to get to description that's close enough --> save it 
4. tweak end_point, end_emotional_scores until all text
    -- get re-running transform 
