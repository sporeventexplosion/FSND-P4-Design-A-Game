# FSND Project 4: Design a Game API

## How to Play

- To play this Concentration game, a User object must first be created. Use the `create_user` method with a username and email to create the user

- Create a new game using `new_game`. Include your username and the number of pairs of cards you want in this game. This value can be between 2 and 64

- Use `make_move` with the urlsafe ID of the game you just created to make a move. Enter the index of the card to uncover. The index and value of a single Move (actually two calls to the `make_move` function) will be returned in the response.

- Match all the cards using make move. When you finish, you will receive a "You Win" message.

- You can now check your score using `get_user_scores` and your username

# Scoring

- Uses history to generate a score

- Each successful match is worth 20 points

- If the player fails to match a matching tile which was previously shown, the score is subtracted by 5 times the number of times the tile has been shown. At the end, if here has not been any failed matches, a bonus score of 5 times the number of pairs in the level is added.

- The score cannot go below 0

- Scoring system based this page: http://dkmgames.com/memory/pairs.php

## Endpoints Method Reference

### `cancel_game`

- Method: *POST*

- Input: *GET_GAME_REQUEST*

- Output: *StringMessage*

- Cancels the game with the specified `urlsafe_game_key`. Only works if the game is not over.

### `create_user`

- Method: *POST*

- Input: *USER_REQUEST*

- Output: *StringMessage*

- Creates a user with the specified username and email, both of which are required and limited to 500 characters. Returns a `ConflictException` if the username is already taken.

### `get_average_moves`

- Method: *GET*

- Input: None

- Output: *StringMessage*

- Returns a message containing the average number of moves elapsed in all active games. This value is cached when a game is created and may not reflect the latest changes. Returns a "Average moves has not been cached" `StringMessage` if not cached.

### `get_game`

- Method: *GET*

- Input: *GET_GAME_REQUEST*

- Output: *GameForm*

- Returns the game with the ID specified in the request. Returns a 404 `NotFoundException` if not found.

### `get_game_history`

- Method: *GET*

- Input: *GET_GAME_REQUEST*

- Output: *HistoryForm*

- Returns a HistoryForm with a list of HistoryMoveForms, each representing a move (two card operations that uncover or do not uncover the pair of cards). Each HistoryMoveForm has a `matched` attribute indicating whether a pair of cards have been matched in this move.

### `get_high_scores`

- Method: *GET*

- Input: *HIGH_SCORE_REQUEST*

- Output: *ScoreForms*

- Returns a ScoreForms in descending order of score. A limit (must be a positive integer) can be specified for the maximum number of entries to fetch.

### `get_scores`

- Method: *GET*

- Input: None

- Output: *ScoreForms*

- Returns a ScoreForms containing every score recorded.

### `get_user_games`

- Method: *GET*

- Input: *USER_REQUEST*

- Output: *GameForms*

- Returns GameForms containing every active (non-finished) game of the user specified.

### `get_user_rankings`

- Method: *GET*

- Input: None

- Output: *RankingForms*

- Returns a RankingForms containing the username of each user and the user's performance (the average score of a user), sorted in descending order.

### `get_user_scores`

- Method: *GET*

- Input: *USER_REQUEST*

- Output: *ScoreForms*

- Returns a list of ScoreForms containing every score of the specified user.

### `make_move`

- Method: *POST*

- Input: *MAKE_MOVE_REQUEST*

- Output: *GameForm*

- Makes a move in the specified game. Returns a GameForm containing current_choice, the index and value of the requested card. If this is the second card in a move (a pair of cards), the previous_choice attribute contains the index and value of the first choice in the move. If the values of the two cards chosen match, they are uncovered. The game is ended when all cards are matched and uncovered.

### `new_game`

- Method: *POST*

- Input: *NEW_GAME_REQUEST*

- Output: *GameForm*

- Creates a new game in the name of the specified user with the specified number of pairs of cards (must be between 2 and 64 inclusive). Returns GameForm with the key to the newly created game.

 - **get_high_scores**
    - Remember how you defined a score in Task 2?
    Now we will use that to generate a list of high scores in descending order, a leader-board!
    - Accept an optional parameter `number_of_results` that limits the number of results returned.
    - Note: If you choose to implement a 2-player game this endpoint is not required.

 - **get_user_rankings**
    - Come up with a method for ranking the performance of each player.
      For "Guess a Number" this could be by winning percentage with ties broken by the average number of guesses.
    - Create an endpoint that returns this player ranking. The results should include each Player's name and the 'performance' indicator (eg. win/loss ratio).

