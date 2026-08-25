from playwright.sync_api import sync_playwright

FORM_URL = "https://august2026karnataka.dicewebfreelancers.com/"

with sync_playwright() as p:

    browser = p.chromium.launch(headless=False)

    page = browser.new_page()

    print("Opening website...")

    page.goto(
        FORM_URL,
        wait_until="domcontentloaded",
        timeout=60000
    )

    print("\nGo through the website manually:")
    print("1. Choose the car category")
    print("2. Open the actual advertisement form")
    print("3. DO NOT submit")
    print()

    input("When the actual car advertisement form is visible, press ENTER...")

    print("\n" + "=" * 80)
    print("FORM URL")
    print("=" * 80)

    print(page.url)

    print("\n" + "=" * 80)
    print("PAGE TITLE")
    print("=" * 80)

    print(page.title())

    print("\n" + "=" * 80)
    print("INPUT FIELDS")
    print("=" * 80)

    inputs = page.locator("input")

    print("Number of input fields:", inputs.count())

    for i in range(inputs.count()):

        element = inputs.nth(i)

        try:

            print("\nINPUT", i)

            print("type     :", element.get_attribute("type"))
            print("name     :", element.get_attribute("name"))
            print("id       :", element.get_attribute("id"))
            print("placeholder:", element.get_attribute("placeholder"))
            print("value    :", element.get_attribute("value"))
            print("aria-label:", element.get_attribute("aria-label"))

        except Exception as e:

            print("Could not inspect input:", e)

    print("\n" + "=" * 80)
    print("SELECT FIELDS")
    print("=" * 80)

    selects = page.locator("select")

    print("Number of select fields:", selects.count())

    for i in range(selects.count()):

        element = selects.nth(i)

        try:

            print("\nSELECT", i)

            print("name:", element.get_attribute("name"))
            print("id:", element.get_attribute("id"))

            options = element.locator("option")

            print("Options:", options.count())

            for j in range(min(options.count(), 30)):

                option = options.nth(j)

                print(
                    "  ",
                    j,
                    "|",
                    option.inner_text(),
                    "| value=",
                    option.get_attribute("value")
                )

        except Exception as e:

            print("Could not inspect select:", e)

    print("\n" + "=" * 80)
    print("TEXTAREAS")
    print("=" * 80)

    textareas = page.locator("textarea")

    print("Number of textarea fields:", textareas.count())

    for i in range(textareas.count()):

        element = textareas.nth(i)

        print("\nTEXTAREA", i)

        print("name:", element.get_attribute("name"))
        print("id:", element.get_attribute("id"))
        print("placeholder:", element.get_attribute("placeholder"))

    print("\n" + "=" * 80)
    print("BUTTONS")
    print("=" * 80)

    buttons = page.locator("button")

    print("Number of buttons:", buttons.count())

    for i in range(buttons.count()):

        element = buttons.nth(i)

        try:

            print(
                "\nBUTTON",
                i,
                "| text=",
                element.inner_text(),
                "| type=",
                element.get_attribute("type"),
                "| name=",
                element.get_attribute("name"),
                "| id=",
                element.get_attribute("id")
            )

        except:
            pass

    print("\n" + "=" * 80)
    print("LINKS")
    print("=" * 80)

    links = page.locator("a")

    print("Number of links:", links.count())

    for i in range(min(links.count(), 100)):

        element = links.nth(i)

        try:

            text = element.inner_text().strip()
            href = element.get_attribute("href")

            if text:

                print(
                    i,
                    "|",
                    text,
                    "|",
                    href
                )

        except:
            pass

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)

    input("\nPress ENTER to close browser...")

    browser.close()