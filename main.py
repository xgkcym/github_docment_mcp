from src.ui.index import create_app



if __name__ == "__main__":
    try:
        demo = create_app()
        demo.launch()
    except Exception as e:
        print(e)