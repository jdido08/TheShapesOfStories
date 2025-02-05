2/3/2025:
- create system for creating stories 
    - create system for identify protoganist 
    - create system for determing font + colors 
- need to figure out font sizes for: [should I have sizes]
   -- 6x6 [same as 12x12]
   -- 12x12 [same as 6x6]
   -- 12x36 [this is actually different --> same font as 12x12 but story needs to be more indepth and detailed]
- add space at the end of phrase (so there's non spaces between component text)
- need to do writeup about story walls
  -- what does the shape of your favorite stories reveal about you?


- figure out size offerings: Done
    - Book
        - Amazon
        - Lulu
    - Canvas
    - Poster 
    - T-Shirt


inputs:
- title, author, year, (protoganist this could be done programctically) 
- determine story data 
--> create prompt to determine background color, font color, border color, font 
- create story shape 

-- create story one by one 



1/31/2025:
- descriptors creation setup good for now but can be optimized for sure but moving on for right now -- done 

need to do:
- format/style for protognist --> done 
- download all font that could be used to computer -- done
- make the title font bold -- done
- make some shape functions e.g. step-by-step parameterized  -- done
- add some checks to make sure I dont get into a death spiral of llm api calls -- done
- dont use net chars for last sections  -- done



1/16/2025:
- need better handling for story shape descriptors
- 

- change adjust descriptors 
- ideas for story segment descriptors:
    - net char adjuster
    - llm bias adjustment 
    - explicit checks for character names
    - if len is materially off then just restart 

- make character text font bigger own parameter 


1/24/2025:
- need to add author to story data
- add protogonst to the story_data file name 
- have option to for setting wrap inches color -- i think we should set it as border colorS --> DONE
- add protogonst to story shape -- bottom right corner 
- download all font that could be used to computer
- make the title font bold 
- refine descriptors prompt to not use protoganist name -- done 
- need to come up with some sort of multiple color scheme - should have different colors for different protoganst at least 

1/21/2024:
- font's not working for story data
    - get claude to pick font's invididually 
    - make sure fotn is installed 
- need to use o1 for story data and need to emphasize that descriptions should be of real things 
    - maybe not -- im going back and changing prompt. I want to make sure descriptiosn have details from the summary
    - I also want to provide more guidance on dividng up major peices. 
- have option to for setting wrap inches color -- i think we should set it as border colorS


1/20/2025:
- support title for line
- support hex colors


1/19/2025 Updates:
1. Determineing story_data is probably better off creating a model like o1 (some reasoning model)
    - refine story data prompt + code/logic for processing 
    - these changes are needed giving we are going to use a reasoning model
    - i think a reasoning model is going to work better for a complex task like this
2. Figure out colors / font styling 
    - figure out story font
    - figure out story colors 
        - 3 colors:
            1. arc + title 
            2. background 
            3. border 
    - need a prompt to figure these things out 
3. Figure out way to feed in story data from excel sheet to create story plot 


Workflow:
1. Create prompt for o1
2. manually copy and paste prompt into o1 
3. copy and paste json into vs code
4. process json
5. generate shape
6. manually inspect shape / make changes 
7. ask AI to inspect shape (NEED PROMPT -- probably use o1 again)



1/16/2025 Update:
_______
- update logic around arc descriptions; probably switch to use claude and change prompt
- figure out colors 
- figure out fonts 
________

- try things on 10 different books 

______

- generate a ton 6x6 
- order prototype 











Update:
- different size canvas is the future; people can mix and match
- pastel colors to begin with 
- on canvas -- done 
    - top; author, year of book -- done
    - bottom: shapes of stories branding -- done
- need to:
    - refine logic for generating text; if outside acceptable range then quick so I can mannually adjust --> done
    - refine logic for generate arc text 
    - refine logic for creating smoother curves without truncations -- done




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
