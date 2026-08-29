from playwright.sync_api import sync_playwright

FORM_URL = "https://august2026karnataka.dicewebfreelancers.com/"


def main():

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False)

        context = browser.new_context()

        page = context.new_page()

        page.goto(
            FORM_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        print()
        print("=" * 80)
        print("LOGIN / POST AD PAGE")
        print("=" * 80)

        input(
            "Open the Post Ad form completely, then press ENTER..."
        )

        print()
        print("=" * 80)
        print("ALL INPUT / TEXTAREA / SELECT CONTROLS")
        print("=" * 80)

        controls = page.locator(
            "input, textarea, select"
        )

        count = controls.count()

        print("TOTAL CONTROLS:", count)
        print()

        for i in range(count):

            control = controls.nth(i)

            try:

                tag = control.evaluate(
                    "(el) => el.tagName"
                )

                control_type = control.get_attribute("type")
                name = control.get_attribute("name")
                element_id = control.get_attribute("id")
                value = control.get_attribute("value")
                placeholder = control.get_attribute("placeholder")
                class_name = control.get_attribute("class")

                print("-" * 80)
                print("CONTROL:", i)
                print("TAG:", tag)
                print("TYPE:", control_type)
                print("NAME:", name)
                print("ID:", element_id)
                print("VALUE:", value)
                print("PLACEHOLDER:", placeholder)
                print("CLASS:", class_name)

                if tag == "SELECT":

                    options = control.locator("option")

                    print(
                        "OPTIONS:",
                        options.count()
                    )

                    for j in range(
                        min(options.count(), 30)
                    ):

                        option = options.nth(j)

                        print(
                            "   ",
                            j,
                            "| value =",
                            option.get_attribute("value"),
                            "| text =",
                            option.inner_text().strip()
                        )

            except Exception as error:

                print(
                    "ERROR:",
                    error
                )

        print()
        print("=" * 80)
        print("FORM HTML STRUCTURE")
        print("=" * 80)

        # Print the HTML around the main form.
        forms = page.locator("form")

        print(
            "FORMS FOUND:",
            forms.count()
        )

        for i in range(forms.count()):

            try:

                html = forms.nth(i).evaluate(
                    "(el) => el.outerHTML"
                )

                print()
                print(
                    f"FORM {i} HTML:"
                )

                print(html[:30000])

            except Exception as error:

                print(
                    "Could not read form:",
                    error
                )

        input(
            "Press ENTER to close browser..."
        )

        browser.close()


if __name__ == "__main__":
    main()