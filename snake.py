import random
import tkinter as tk
from collections import deque

CELL = 20
COLS = 30
ROWS = 20
DELAY = 110  # ms

DIRS = {
    "Up": (0, -1),
    "Down": (0, 1),
    "Left": (-1, 0),
    "Right": (1, 0),
}
OPPOSITE = {"Up": "Down", "Down": "Up", "Left": "Right", "Right": "Left"}


class Snake:
    def __init__(self, name, body, direction, head_color, body_color):
        self.name = name
        self.body = body
        self.direction = direction
        self.next_direction = direction
        self.head_color = head_color
        self.body_color = body_color
        self.score = 0
        self.alive = True


def in_bounds(p):
    return 0 <= p[0] < COLS and 0 <= p[1] < ROWS


def neighbors(p):
    for name, (dx, dy) in DIRS.items():
        q = (p[0] + dx, p[1] + dy)
        if in_bounds(q):
            yield name, q


def flood_area(start, blocked, limit):
    """start에서 갈 수 있는 칸 수 (limit에 도달하면 중단)."""
    seen = {start}
    queue = deque([start])
    while queue and len(seen) < limit:
        cur = queue.popleft()
        for _, q in neighbors(cur):
            if q not in blocked and q not in seen:
                seen.add(q)
                queue.append(q)
    return len(seen)


def ai_choose_direction(me, other, food):
    """BFS로 사과까지 최단 경로를 찾고, 안전하지 않으면 가장 넓은 공간 쪽으로 이동."""
    head = me.body[0]
    # 양쪽 뱀의 꼬리는 다음 턴에 빠지므로 막힌 칸에서 제외
    blocked = set(me.body[:-1]) | set(other.body[:-1])
    # 상대 머리가 다음에 갈 수 있는 칸은 정면충돌 위험이 있으므로 피한다
    danger = {q for _, q in neighbors(other.body[0])} if other.alive else set()

    def safe_moves(avoid_danger):
        moves = []
        for name, q in neighbors(head):
            if name == OPPOSITE[me.direction] or q in blocked:
                continue
            if avoid_danger and q in danger:
                continue
            moves.append((name, q))
        return moves

    # 사과까지 BFS
    first_step = {}
    queue = deque()
    for name, q in safe_moves(True):
        first_step[q] = name
        queue.append(q)
    visited = set(first_step)
    target_move = None
    while queue:
        cur = queue.popleft()
        if cur == food:
            target_move = first_step[cur]
            break
        for _, q in neighbors(cur):
            if q not in blocked and q not in visited:
                visited.add(q)
                first_step[q] = first_step[cur]
                queue.append(q)

    # 사과 방향으로 가도 갇히지 않는지 확인
    if target_move:
        dx, dy = DIRS[target_move]
        nxt = (head[0] + dx, head[1] + dy)
        if flood_area(nxt, blocked | {head}, len(me.body) + 1) > len(me.body):
            return target_move

    # 가장 넓은 공간이 남는 방향 선택
    best, best_area = None, -1
    for avoid in (True, False):
        for name, q in safe_moves(avoid):
            area = flood_area(q, blocked | {head}, COLS * ROWS)
            if area > best_area:
                best, best_area = name, area
        if best:
            break
    return best or me.direction


class SnakeGame:
    def __init__(self, root):
        self.root = root
        root.title("뱀 게임 - 사람 vs AI")
        root.resizable(False, False)

        self.score_var = tk.StringVar()
        tk.Label(root, textvariable=self.score_var, font=("Arial", 14)).pack()

        self.canvas = tk.Canvas(
            root, width=COLS * CELL, height=ROWS * CELL, bg="black", highlightthickness=0
        )
        self.canvas.pack()

        root.bind("<KeyPress>", self.on_key)
        self.reset()
        self.tick()

    def reset(self):
        mid = ROWS // 2
        self.human = Snake(
            "사람", [(5 - i, mid + 3) for i in range(3)], "Right", "#00BFFF", "#1E6FA8"
        )
        self.ai = Snake(
            "AI", [(COLS - 6 + i, mid - 3) for i in range(3)], "Left", "#FFD700", "#B8860B"
        )
        self.snakes = [self.human, self.ai]
        self.game_over = False
        self.paused = False
        self.result = ""
        self.place_food()
        self.draw()

    def place_food(self):
        occupied = set(self.human.body) | set(self.ai.body)
        free = [(x, y) for x in range(COLS) for y in range(ROWS) if (x, y) not in occupied]
        self.food = random.choice(free) if free else None

    def on_key(self, event):
        key = event.keysym
        if key in DIRS:
            if key != OPPOSITE[self.human.direction]:
                self.human.next_direction = key
        elif key in ("space", "p", "P"):
            if not self.game_over:
                self.paused = not self.paused
                self.draw()
        elif key in ("r", "R", "Return") and self.game_over:
            self.reset()
        elif key == "Escape":
            self.root.destroy()

    def tick(self):
        if not self.game_over and not self.paused:
            self.step()
        self.draw()
        top = max(self.human.score, self.ai.score)
        self.root.after(max(50, DELAY - top * 2), self.tick)

    def step(self):
        h, a = self.human, self.ai
        a.next_direction = ai_choose_direction(a, h, self.food)

        new_heads = {}
        for s in (h, a):
            s.direction = s.next_direction
            dx, dy = DIRS[s.direction]
            new_heads[s] = (s.body[0][0] + dx, s.body[0][1] + dy)

        eats = {s: new_heads[s] == self.food for s in (h, a)}
        # 이번 이동에서 꼬리가 빠지는 뱀은 꼬리 칸이 비게 된다
        bodies = {s: s.body if eats[s] else s.body[:-1] for s in (h, a)}

        for s in (h, a):
            o = a if s is h else h
            p = new_heads[s]
            if (
                not in_bounds(p)
                or p in bodies[s]
                or p in bodies[o]
                or p == new_heads[o]
            ):
                s.alive = False

        if not (h.alive and a.alive):
            for s in (h, a):
                if s.alive:
                    s.body.insert(0, new_heads[s])
                    if not eats[s]:
                        s.body.pop()
                    else:
                        s.score += 1
            self.game_over = True
            if h.alive:
                self.result = "사람 승리!"
            elif a.alive:
                self.result = "AI 승리!"
            else:
                self.result = "무승부"
            return

        ate = False
        for s in (h, a):
            s.body.insert(0, new_heads[s])
            if eats[s]:
                s.score += 1
                ate = True
            else:
                s.body.pop()
        if ate:
            self.place_food()
            if self.food is None:
                self.game_over = True
                self.result = (
                    "사람 승리!" if h.score > a.score
                    else "AI 승리!" if a.score > h.score
                    else "무승부"
                )

    def draw(self):
        c = self.canvas
        c.delete("all")
        self.score_var.set(f"사람: {self.human.score}    AI: {self.ai.score}")

        if self.food:
            fx, fy = self.food
            c.create_oval(
                fx * CELL + 2, fy * CELL + 2, (fx + 1) * CELL - 2, (fy + 1) * CELL - 2,
                fill="red", outline="",
            )

        for s in self.snakes:
            for i, (x, y) in enumerate(s.body):
                c.create_rectangle(
                    x * CELL + 1, y * CELL + 1, (x + 1) * CELL - 1, (y + 1) * CELL - 1,
                    fill=s.head_color if i == 0 else s.body_color, outline="",
                )

        if self.game_over:
            self.center_text(f"{self.result}\nR 키: 다시 시작", "white")
        elif self.paused:
            self.center_text("일시정지", "yellow")

    def center_text(self, text, color):
        self.canvas.create_text(
            COLS * CELL // 2, ROWS * CELL // 2,
            text=text, fill=color, font=("Arial", 24, "bold"), justify="center",
        )


if __name__ == "__main__":
    root = tk.Tk()
    SnakeGame(root)
    root.mainloop()
