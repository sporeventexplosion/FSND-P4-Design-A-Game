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

- Method: **POST**

- Input: **GET_GAME_REQUEST**

- Output: **StringMessage**

- Cancels the game with the specified `urlsafe_game_key`. Only works if the game is not over.

### `create_user`

- Method: **POST**

- Input: **USER_REQUEST**

- Output: **StringMessage**

- Creates a user with the specified username and email, both of which are required and limited to 500 characters. Returns a `ConflictException` if the username is already taken.

### `get_average_moves`

- Method: **GET**

- Input: None

- Output: **StringMessage**

- Returns a message containing the average number of moves elapsed in all active games. This value is cached when a game is created and may not reflect the latest changes. Returns a "Average moves has not been cached" `StringMessage` if not cached.

### `get_game`

- Method: **GET**

- Input: **GET_GAME_REQUEST**

- Output: **GameForm**

- Returns the game with the ID specified in the request. Returns a 404 `NotFoundException` if not found.

### `get_game_history`

- Method: **GET**

- Input: **GET_GAME_REQUEST**

- Output: **HistoryForm**

- Returns a HistoryForm with a list of HistoryMoveForms, each representing a move (two card operations that uncover or do not uncover the pair of cards). Each HistoryMoveForm has a `matched` attribute indicating whether a pair of cards have been matched in this move.

### `get_high_scores`

- Method: **GET**

- Input: **HIGH_SCORE_REQUEST**

- Output: **ScoreForms**

- Returns a ScoreForms in descending order of score. A limit (must be a positive integer) can be specified for the maximum number of entries to fetch.

### `get_scores`

- Method: **GET**

- Input: None

- Output: **ScoreForms**

- Returns a ScoreForms containing every score recorded.

### `get_user_games`

- Method: **GET**

- Input: **USER_REQUEST**

- Output: **GameForms**

- Returns GameForms containing every game of the user specified.

### `get_user_rankings`

- Method: **GET**

- Input: None

- Output: **RankingForms**

- Returns a RankingForms containing the username of each user and the user's performance (the average score of a user), sorted in descending order.

### `get_user_scores`

- Method: **GET**

- Input: **USER_REQUEST**

- Output: **ScoreForms**

- Returns a list of ScoreForms containing every score of the specified user.

### `make_move`

- Method: **POST**

- Input: **MAKE_MOVE_REQUEST**

- Output: **GameForm**

- Makes a move in the specified game. Returns a GameForm containing current_choice, the index and value of the requested card. If this is the second card in a move (a pair of cards), the previous_choice attribute contains the index and value of the first choice in the move. If the values of the two cards chosen match, they are uncovered. The game is ended when all cards are matched and uncovered.

### `new_game`

- Method: **POST**

- Input: **NEW_GAME_REQUEST**

- Output: **GameForm**

- Creates a new game in the name of the specified user with the specified number of pairs of cards (must be between 2 and 64 inclusive). Returns GameForm with the key to the newly created game.

## ProtoRPC Message Containers

### `USER_REQUEST`

Used for querying information about a user and creating new users.

- **username**: String. Required

- **email**: String. Required only when creating a user

### `NEW_GAME_REQUEST`

Used for creating a game. Contains NewGameForm (see below).

### `GET_GAME_REQUEST`

Used for fetching a game using the URL-safe key of that game.

- **urlsafe_game_key**: String containing the URL-safe key of a game

### `MAKE_MOVE_REQUEST`

Used to make a move in an existing game. Contains MakeMoveForm (see below).

- **urlsafe_game_key**: String containing the URL-safe key of a game

### `HIGH_SCORE_REQUEST`

Used to request a list of high scores.

- **limit**: Integer, optional. For specifying the maximum number of scores to fetch (minimum is 1)


## Endpoint Message Classes

### `CardForm`

Represents a single card in a game of Concentration. Used in various parts of the API.

- **index**: Integer, required. The index of the card in a list of cards

- **value**: Integer, required. The value of the card at that index

### `GameForm`

Represents a single game.

- **urlsafe_key**: String, required. The URL-safe key of this game

- **username**: String, required. The username of the user that created this game

- **moves**: Integer, required. The number of moves elapsed in the game.

- **num_pairs**: Integer, required. The number of pairs of cards in the game.

- **previous_choice**: `CardForm` message. Present if one card in a pair has been uncovered in the game and contains information about that card.

- **current_choice**: `CardForm` message. Present if the current GameForm operation uncovers a card and contains information about this card.

- **shown_cards**: `CardForm` message repeated. A list of cards that have been uncovered

- **game_over**: Boolean, required. Whether the game is over.

- **message**: String. A message for the user, or an empty string if there is no message.

### `NewGameForm`

Used to create a new game.

- **username**: String, required. The username of the user creating this game

- **num_pairs**: Integer, required. The number of pairs of cards in the game. Actual number of cards will be twice this number.

### `MakeMoveForm`

Used to make a move in an active game (uncover a single card).

- **card**: Integer, required. The index of the card to uncover

### `ScoreForm`

Represents a single score entry.

- **username**: String, required. The username of the user that created this score

- **datetime**: String, required. The date and time on which this score was created

- **score**: Integer, required. The score value of the game that resulted in this score

- **moves**: Integer, required. The number of moves played in the game that resulted in this score

- **time_used**: Integer, required. The number of seconds taken to finish the game that resulted in this score

### `ScoreForms`

Represents multiple scores, as returned by an API endpoint.

- **items**: `ScoreForm` message, repeated. A list of scores, meaning depends on the specific API.

### `GameForms`

Represents multiple games, as returned by an API endpoint.

- **items**: `GameForm` message, repeated. A list of games, meaning depends on the specific API.

### `RankingForm`

Represents the ranking entry for a single user.

- **username**: String, required. The username of the user with this ranking

- **performance**: Float, required. The "performance indicator" of the user, in this case the average score of all of the user's games.

### `RankingForms`

Represents multiple user rankings, as returned by an API endpoint.

- **items**: `RankingForm` message, repeated. A list of rankings, meaning depends on the specific API.

### `HistoryMoveForm`

Represents a single move in a histor log consisting of two cards.

- **card_1**: `CardForm` message, required. The first card in this move

- **card_2**: `CardForm` message, required. The second card in this move

### `HistoryForm`

Represents the entire move history for a game.

- **moves**: `HistoryMoveForm` message, repeated. The moves elapsed in the given game.

### `StringMessage`

A general-purpose string message for returning text data to the client in non-error circumstances.

- **message**: String, required. The message to be passed
