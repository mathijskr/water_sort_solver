import Relude.Extra.Tuple
import qualified Data.Set as Set
import Data.Maybe
import Data.Either

type Color = Int
type Stack a = [a]
type Cylinder = Stack Color
type Index = Int
type CylinderHeight = Int
type Cylinders = Index -> Maybe Cylinder
type Configuration = (Cylinders, CylinderHeight)
type Move = (Index, Index) -- From Cylinder, To Cylinder
type Solution = [Move]
type ExploredStates = Set.Set [Cylinder]

main :: IO()
main = interact $ (either (\_ -> "no solution :(\n") ((++ "\n") . show)) . (solve mempty) . parseConfiguration


parseConfiguration :: String -> Configuration
parseConfiguration = (toSnd findHeight) . (flip lookup) . (zip [0..]) . (fmap readCylinder) . lines

toListC :: Cylinders -> [Cylinder]
toListC = takeWhileJust . (flip fmap) [0..]

findHeight :: (Index -> Maybe Cylinder) -> Int
findHeight = maximum . (fmap length) . toListC

readCylinder :: String -> Cylinder
readCylinder = (fmap read) . (filter (/= "E")) . words

-- Manually keep track of explored states to prevent loops.
solve :: ExploredStates -> Configuration -> Either ExploredStates Solution
solve explored_states configuration
  | isSolved configuration = (Right [])
  | Set.member (toListC $ fst configuration) explored_states = (Left explored_states)
  | allowedMoves configuration == [] = (Left explored_states)
  | otherwise = let moves = allowedMoves configuration
                    next_explored_states = (Set.insert (toListC $ fst configuration) explored_states)
                    possible_solutions = fmap (\move -> maybe (Left next_explored_states)
                                                              ((either Left (Right . ((:) move))) . (solve next_explored_states))
                                                              (applyMove configuration move)) moves
                in case partitionEithers possible_solutions of
                     (_, (solution:_)) -> (Right solution)
                     (all_explored_states, _) -> (Left $ foldr Set.union next_explored_states all_explored_states)

isSolved :: Configuration -> Bool
isSolved (cylinders, max_height) = (all (isComplete max_height) . (filter (not . empty)) . toListC) cylinders

isComplete :: CylinderHeight -> Cylinder -> Bool
isComplete max_height cylinder = (height cylinder) == max_height && 1 == (numberOfColors cylinder)

numberOfColors :: Cylinder -> Int
numberOfColors = Set.size . Set.fromList

allowedMoves :: Configuration -> [Move]
allowedMoves configuration@(cylinders, _) = let n = length $ toListC cylinders
                                                two_permutations = [(a, b) | a <- [0 .. (n - 1)], b <- [0 .. (n - 1)], a /= b]
                                            in filter (isValidAndProgressiveMove configuration) two_permutations

isValidAndProgressiveMove :: Configuration -> Move -> Bool
isValidAndProgressiveMove (cylinders, max_height) (from_index, to_index) =
  let check from_cylinder to_cylinder =
        ((empty to_cylinder) && (not $ empty from_cylinder)) && (numberOfColors from_cylinder > 1) || -- Pour from non empty cylinder to empty cylinder.
        (maybe False (\from_color -> maybe False (\to_color -> from_color == to_color && (height to_cylinder) < max_height) (peek to_cylinder)) (peek from_cylinder)) -- Pour from non empty cylinder to non-full cylinder with same color on top.
  in maybe False (\from_cylinder -> maybe False (\to_cylinder -> check from_cylinder to_cylinder) (cylinders to_index)) (cylinders from_index)

applyMove :: Configuration -> Move -> Maybe Configuration
applyMove (cylinders, max_height) (from_index, to_index) =
  cylinders from_index
  >>= \from_cylinder -> cylinders to_index
  >>= \to_cylinder -> pour max_height from_cylinder to_cylinder
  >>= \(new_from_cylinder, new_to_cylinder) -> let new_cylinders index = case () of
                                                     _ | index == from_index -> (Just new_from_cylinder)
                                                     _ | index == to_index -> (Just new_to_cylinder)
                                                     _ -> cylinders index
                                               in (Just (new_cylinders, max_height))

pour :: CylinderHeight -> Cylinder -> Cylinder -> Maybe (Cylinder, Cylinder)
pour max_height from_cylinder to_cylinder = pop from_cylinder >>=
                                            \(color, new_from_cylinder) ->
                                              let new_to_cylinder = push color to_cylinder in
                                                if (height new_to_cylinder) < max_height && (peek new_from_cylinder) == (Just color)
                                                then pour max_height new_from_cylinder new_to_cylinder
                                                else (Just (new_from_cylinder, new_to_cylinder))

push :: a -> Stack a -> Stack a
push e s = (e:s)

pop :: Stack a -> Maybe (a, Stack a)
pop [] = Nothing
pop (e:s) = (Just (e,s))

peek :: Stack a -> Maybe a
peek [] = Nothing
peek (e:_) = (Just e)

empty :: Stack a -> Bool
empty = null

height :: Stack a -> Int
height = length

takeWhileJust :: [Maybe a] -> [a]
takeWhileJust = catMaybes . takeWhile isJust
