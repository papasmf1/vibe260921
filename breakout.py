import tkinter as tk

WIDTH, HEIGHT = 600, 500
PADDLE_W, PADDLE_H = 90, 12
BALL_R = 8
ROWS, COLS = 6, 10
BRICK_W, BRICK_H = 54, 20
BRICK_GAP = 4
COLORS = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#3498db", "#9b59b6"]


class Breakout:
    def __init__(self, root):
        self.root = root
        root.title("블럭깨기")
        root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="black")
        self.canvas.pack()
        self.left = self.right = False
        root.bind("<KeyPress-Left>", lambda e: setattr(self, "left", True))
        root.bind("<KeyRelease-Left>", lambda e: setattr(self, "left", False))
        root.bind("<KeyPress-Right>", lambda e: setattr(self, "right", True))
        root.bind("<KeyRelease-Right>", lambda e: setattr(self, "right", False))
        root.bind("<Motion>", self.on_mouse)
        root.bind("<space>", self.on_space)
        root.bind("r", lambda e: self.reset())
        self.reset()
        self.loop()

    def reset(self):
        self.canvas.delete("all")
        self.score = 0
        self.lives = 3
        self.state = "ready"  # ready, playing, over, win
        self.bricks = {}
        total_w = COLS * (BRICK_W + BRICK_GAP) - BRICK_GAP
        x0 = (WIDTH - total_w) // 2
        for r in range(ROWS):
            for c in range(COLS):
                x = x0 + c * (BRICK_W + BRICK_GAP)
                y = 50 + r * (BRICK_H + BRICK_GAP)
                item = self.canvas.create_rectangle(
                    x, y, x + BRICK_W, y + BRICK_H, fill=COLORS[r], outline="")
                self.bricks[item] = 10 * (ROWS - r)
        self.paddle_x = (WIDTH - PADDLE_W) / 2
        self.paddle = self.canvas.create_rectangle(
            0, HEIGHT - 30, PADDLE_W, HEIGHT - 30 + PADDLE_H, fill="white")
        self.ball = self.canvas.create_oval(0, 0, BALL_R * 2, BALL_R * 2, fill="white")
        self.hud = self.canvas.create_text(10, 10, anchor="nw", fill="white",
                                           font=("Arial", 14))
        self.msg = self.canvas.create_text(WIDTH / 2, HEIGHT / 2, fill="white",
                                           font=("Arial", 20, "bold"), justify="center")
        self.place_ball_on_paddle()
        self.update_ui()

    def place_ball_on_paddle(self):
        self.bx = self.paddle_x + PADDLE_W / 2
        self.by = HEIGHT - 30 - BALL_R
        self.vx, self.vy = 4, -5
        self.state = "ready"

    def on_mouse(self, e):
        self.paddle_x = min(max(e.x - PADDLE_W / 2, 0), WIDTH - PADDLE_W)

    def on_space(self, e):
        if self.state == "ready":
            self.state = "playing"
        elif self.state in ("over", "win"):
            self.reset()

    def update_ui(self):
        self.canvas.itemconfig(self.hud, text=f"점수: {self.score}   생명: {'♥' * self.lives}")
        texts = {
            "ready": "스페이스바: 시작\n← → 또는 마우스로 이동",
            "over": f"게임 오버! 점수 {self.score}\n스페이스바: 다시 시작",
            "win": f"클리어! 점수 {self.score}\n스페이스바: 다시 시작",
        }
        self.canvas.itemconfig(self.msg, text=texts.get(self.state, ""))

    def step(self):
        if self.left:
            self.paddle_x = max(self.paddle_x - 8, 0)
        if self.right:
            self.paddle_x = min(self.paddle_x + 8, WIDTH - PADDLE_W)
        py = HEIGHT - 30
        self.canvas.coords(self.paddle, self.paddle_x, py,
                           self.paddle_x + PADDLE_W, py + PADDLE_H)

        if self.state == "ready":
            self.bx = self.paddle_x + PADDLE_W / 2
        elif self.state == "playing":
            self.bx += self.vx
            self.by += self.vy
            # 벽 충돌
            if self.bx - BALL_R <= 0:
                self.bx, self.vx = BALL_R, abs(self.vx)
            elif self.bx + BALL_R >= WIDTH:
                self.bx, self.vx = WIDTH - BALL_R, -abs(self.vx)
            if self.by - BALL_R <= 0:
                self.by, self.vy = BALL_R, abs(self.vy)
            # 패들 충돌
            if (self.vy > 0 and py <= self.by + BALL_R <= py + PADDLE_H + 6
                    and self.paddle_x - BALL_R <= self.bx <= self.paddle_x + PADDLE_W + BALL_R):
                offset = (self.bx - (self.paddle_x + PADDLE_W / 2)) / (PADDLE_W / 2)
                self.vx = offset * 6
                self.vy = -abs(self.vy)
                self.by = py - BALL_R
            # 블록 충돌
            hit = self.canvas.find_overlapping(
                self.bx - BALL_R, self.by - BALL_R, self.bx + BALL_R, self.by + BALL_R)
            for item in hit:
                if item in self.bricks:
                    self.score += self.bricks.pop(item)
                    x1, y1, x2, y2 = self.canvas.coords(item)
                    self.canvas.delete(item)
                    # 충돌 방향 판단
                    if x1 <= self.bx <= x2:
                        self.vy = -self.vy
                    else:
                        self.vx = -self.vx
                    break
            if not self.bricks:
                self.state = "win"
            # 바닥으로 떨어짐
            if self.by - BALL_R > HEIGHT:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = "over"
                else:
                    self.place_ball_on_paddle()
            self.update_ui()

        self.canvas.coords(self.ball, self.bx - BALL_R, self.by - BALL_R,
                           self.bx + BALL_R, self.by + BALL_R)
        if self.state == "ready":
            self.update_ui()

    def loop(self):
        self.step()
        self.root.after(16, self.loop)


if __name__ == "__main__":
    root = tk.Tk()
    Breakout(root)
    root.mainloop()
