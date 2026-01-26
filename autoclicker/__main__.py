try:
    from .ui import App
except ImportError:
    from autoclicker.ui import App


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
