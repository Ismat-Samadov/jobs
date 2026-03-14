export type Direction = 'up' | 'down' | 'left' | 'right';
export type MonsterColor = 'pink' | 'blue' | 'green' | 'yellow' | 'purple';
export type Difficulty = 'easy' | 'medium' | 'hard';

export interface Monster {
  id: string;
  color: MonsterColor;
  rowStart: number;
  rowEnd: number;
  colStart: number;
  colEnd: number;
}

export interface StarPosition {
  row: number;
  col: number;
}

export interface Level {
  id: number;
  name: string;
  gridSize: number;
  monsters: Array<{
    color: MonsterColor;
    rowStart: number;
    rowEnd: number;
    colStart: number;
    colEnd: number;
  }>;
  stars: StarPosition[];
  par: number;
  difficulty: Difficulty;
}

export interface GameState {
  currentLevel: Level;
  monsters: Monster[];
  moves: number;
  isComplete: boolean;
  isPaused: boolean;
  selectedMonsterId: string | null;
  history: Monster[][];
}

export interface HighScore {
  levelId: number;
  moves: number;
  date: string;
}
