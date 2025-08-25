import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List

import polars as pl
from playwright.sync_api import Page, Playwright, TimeoutError, expect, sync_playwright
from tqdm import tqdm


@dataclass
class Apartment:
    name: str


@dataclass
class Floor:
    name: str
    apartments: List[Apartment]


@dataclass
class Building:
    name: str
    floors: List[Floor]


@dataclass
class Project:
    name: str
    buildings: List[Building]


@dataclass
class Province:
    name: str
    projects: List[Project]


def flatten_buildings(buildings: List[Building]) -> pl.DataFrame:
    flattened_data = []
    for building in buildings:
        for floor in building.floors:
            for apartment in floor.apartments:
                flattened_data.append(
                    {
                        "building": building.name,
                        "floor": floor.name,
                        "apartment": apartment.name,
                    }
                )
    return pl.DataFrame(flattened_data)


def flatten_projects(projects: List[Project]) -> pl.DataFrame:
    flattened_data = []
    for project in projects:
        for building in project.buildings:
            for floor in building.floors:
                for apartment in floor.apartments:
                    flattened_data.append(
                        {
                            "project": project.name,
                            "building": building.name,
                            "floor": floor.name,
                            "apartment": apartment.name,
                        }
                    )
    return pl.DataFrame(flattened_data)


def flatten_nested_structure(provinces: List[Province]):
    flattened_data = []
    for province in provinces:
        for project in province.projects:
            for building in project.buildings:
                for floor in building.floors:
                    for apartment in floor.apartments:
                        flattened_data.append(
                            {
                                "province": province.name,
                                "project": project.name,
                                "building": building.name,
                                "floor": floor.name,
                                "apartment": apartment.name,
                            }
                        )
    return flattened_data


def extract_all_listbox_items_static(page: Page, xpath: str):
    """
    Extracts all visible items from a listbox where all items are in the DOM.
    Assumes the listbox content is already present on the page.
    """
    page.wait_for_load_state(state="networkidle")
    # page.wait_for_load_state(state="domcontentloaded")
    # page.wait_for_load_state(state="load")
    page.wait_for_selector(f"xpath={xpath}", timeout=20000)
    # Selector for the text content within each list item.
    # The text is inside a div with class 'text-om-t16' within an li with role 'option'.
    item_text_selector = f"xpath={xpath}"

    # Get all matching elements and extract their text content
    # .all_text_contents() is efficient for this.
    items = page.locator(item_text_selector).all_text_contents()

    # Clean up whitespace for each item
    cleaned_items = [item.strip() for item in items]

    return cleaned_items


def extract_all_listbox_items(page: Page, xpath: str) -> List:
    """
    Scrolls and extracts all items from a virtualized listbox.
    Assumes the listbox is already open and visible.
    """
    page.wait_for_selector(f"xpath={xpath}")
    # 1. Identify the scrollable container
    # Based on your HTML, the element with data-test-id="virtuoso-scroller" is the one to scroll.
    scrollable_element = page.locator('[data-test-id="virtuoso-scroller"]')
    if scrollable_element.count() == 0:
        return []

    # Selector for individual list items' text content
    # The actual text is inside <div class="mx-2 px-2 py-3 ... text-om-t16">
    item_selector = 'li[role="option"] div.text-om-t16'

    all_items = set()  # Use a set to store unique items

    previous_scroll_height = -1

    while True:
        # 2. Extract all currently visible items
        current_visible_items = page.locator(item_selector).all_text_contents()
        for item_text in current_visible_items:
            all_items.add(item_text.strip())  # Add cleaned text to the set

        # 3. Scroll down
        # Get current scroll height and client height
        current_scroll_height = scrollable_element.evaluate("el => el.scrollHeight")
        current_scroll_top = scrollable_element.evaluate("el => el.scrollTop")
        client_height = scrollable_element.evaluate("el => el.clientHeight")

        # Check if we've reached the bottom
        if current_scroll_top + client_height >= current_scroll_height:
            # If we were already at the bottom and no new content appeared,
            # or if the scroll height hasn't changed, we're done.
            if current_scroll_height == previous_scroll_height:
                logging.debug(
                    "Reached end of scrollable content and no new items appeared."
                )
                break
            # If we've scrolled to the end but scrollHeight *did* change,
            # it might mean new items loaded just at the very end.
            # We'll do one more iteration to ensure we capture them.

        # Scroll down by the height of the visible area
        scrollable_element.evaluate("el => el.scrollBy(0, el.clientHeight)")

        # Update previous scroll height for the next iteration
        previous_scroll_height = current_scroll_height

        # 4. Wait for new content to load
        # A small timeout is often necessary for virtualized lists to render new items.
        page.wait_for_timeout(100)  # Adjust this value if needed

    return list(all_items)


def go_floors(page: Page) -> List[Floor]:
    floor_box = page.locator(f"xpath={FLOOR_BOX_XPATH}")

    page.wait_for_selector(f"xpath={FLOOR_BOXLIST_XPATH}")
    expect(page.locator(f"xpath={FLOOR_BOXLIST_XPATH}"))

    floors = extract_all_listbox_items_static(page, FLOOR_BOXLIST_XPATH)
    logging.debug(f"Floors: {floors}")

    result: List[Floor] = []
    for floor in tqdm(floors):
        try:
            logging.debug(f"Floor: {floor}")
            page.get_by_role("textbox", name="Tầng").fill(floor)
            page.locator(f"xpath={FLOOR_BOXLIST_XPATH}").nth(0).click()

            apartments = extract_all_listbox_items_static(page, APARTMENT_BOXLIST_XPATH)
            logging.debug(f"Apartments: {apartments}")
            result.append(
                Floor(
                    name=floor, apartments=[Apartment(name=item) for item in apartments]
                )
            )
        except TimeoutError as e:
            logging.error(f"{e}, skipping floor {floor}...")
        finally:
            page.keyboard.press("Escape")
            page.keyboard.press("Escape")
            floor_box.click(click_count=1)

    return result


def go_buildings(page: Page) -> List[Building]:
    building_box = page.locator(f"xpath={BUIDING_BOX_XPATH}")

    page.wait_for_selector(f"xpath={BUIDING_BOXLIST_XPATH}")
    expect(page.locator(f"xpath={BUIDING_BOXLIST_XPATH}"))

    buildings = extract_all_listbox_items_static(page, BUIDING_BOXLIST_XPATH)
    logging.debug(f"Buildings: {buildings}")

    result: List[Building] = []

    for building in tqdm(buildings):
        try:
            logging.debug(f"Building: {building}")
            page.get_by_role("textbox", name="Tìm toà/khu").fill(building)
            page.locator(f"xpath={BUIDING_BOXLIST_XPATH}").nth(0).click()
            result.append(Building(name=building, floors=go_floors(page)))
        except TimeoutError as e:
            logging.error(f"{e}, skipping building {building}...")
        finally:
            page.keyboard.press("Escape")
            page.keyboard.press("Escape")
            building_box.click(click_count=1)

    return result


def go_projects(page: Page, province: str) -> List[Project]:
    project_box = page.locator(f"xpath={PROJECT_BOX_XPATH}")

    page.wait_for_selector(f"xpath={PROJECT_BOXLIST_XPATH}")
    projects = extract_all_listbox_items(page, PROJECT_BOXLIST_XPATH)
    logging.debug(f"Projects: {projects}")

    result: List[Project] = []

    for project in tqdm(projects):
        # Construct the expected filename for the parquet file
        parquet_filename = Path(
            f"./dataset/{province.replace(' ', '')}/{project.replace(' ', '')}.parquet"
        )

        # Check if the file already exists
        if parquet_filename.exists():
            logging.info(
                f"Skipping project '{project}' as '{parquet_filename}' already exists."
            )
        else:
            try:
                logging.debug(f"Project: {project}")
                page.get_by_role("textbox", name="Tìm dự án").fill(project)
                page.locator(f"xpath={PROJECT_BOXLIST_XPATH}").nth(0).click()
                result_project = Project(name=project, buildings=go_buildings(page))
                flatten_projects([result_project]).write_parquet(
                    parquet_filename  # Use the constructed filename here
                )
                logging.info(f"Saved {result_project.name} as {parquet_filename}")
            except TimeoutError as e:
                logging.error(f"{e}, skipping project {project}...")
            finally:
                page.keyboard.press("Escape")
                page.keyboard.press("Escape")
                project_box.click(click_count=1)

    return result


def go_provinces(page: Page) -> List[Province]:
    province_box = page.locator(f"xpath={PROVINCE_BOX_XPATH}")

    page.wait_for_selector(f"xpath={PROVINCE_BOX_XPATH}")
    province_box.click()

    # provinces = extract_all_listbox_items_static(page, PROVINCE_BOXLIST_XPATH)[
    #     1:
    # ]  # ignore toan quoc

    result: List[Province] = []

    # for province in tqdm(provinces):
    for province in tqdm(["TP.Hồ Chí Minh"]):
        try:
            logging.debug(f"Province: {province}")
            page.get_by_role("textbox", name="Tỉnh/thành phố").fill(province)
            page.locator(f"xpath={PROVINCE_BOXLIST_XPATH}").nth(0).click()
            result.append(
                Province(
                    name=province, projects=go_projects(page=page, province=province)
                )
            )
        except TimeoutError as e:
            logging.error(f"{e}, skipping province {province}...\n")
        finally:
            page.keyboard.press("Escape")
            page.keyboard.press("Escape")
            province_box.click(click_count=1)

    return result


def run(playwright: Playwright) -> None:
    browser = playwright.firefox.launch(
        headless=False,
        # proxy={
        #     "server": "socks5://127.0.0.1:9050",
        # },
    )
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://onehousing.vn/cong-cu/dinh-gia")

    result = go_provinces(page)

    # ---------------------
    context.close()
    browser.close()


def main():
    logging.basicConfig(level=logging.INFO)
    with sync_playwright() as playwright:
        run(playwright)


if __name__ == "__main__":
    PROVINCE_BOX_XPATH = "/html/body/div[2]/div[4]/div[2]/div/div[2]/div/div[2]/div[1]/div[1]/form/div/div[1]/div/div"
    PROVINCE_BOXLIST_XPATH = "/html/body/div[2]/div[4]/div[2]/div/div[2]/div/div[2]/div[1]/div[1]/form/div/div[1]/div/div[2]/div/ul/li"
    PROJECT_BOX_XPATH = "/html/body/div[2]/div[4]/div[2]/div/div[2]/div/div[2]/div[1]/div[1]/form/div/div[2]/div/div"
    PROJECT_BOXLIST_XPATH = "/html/body/div[2]/div[4]/div[2]/div/div[2]/div/div[2]/div[1]/div[1]/form/div/div[2]/div/div[2]/div/ul/div/div/div/div"
    BUIDING_BOX_XPATH = "/html/body/div[2]/div[4]/div[2]/div/div[2]/div/div[2]/div[1]/div[1]/form/div/div[3]/div/div"
    BUIDING_BOXLIST_XPATH = "/html/body/div[2]/div[4]/div[2]/div/div[2]/div/div[2]/div[1]/div[1]/form/div/div[3]/div/div[2]/div/ul/li"
    FLOOR_BOX_XPATH = "/html/body/div[2]/div[4]/div[2]/div/div[2]/div/div[2]/div[1]/div[1]/form/div/div[4]/div/div"
    FLOOR_BOXLIST_XPATH = "/html/body/div[2]/div[4]/div[2]/div/div[2]/div/div[2]/div[1]/div[1]/form/div/div[4]/div/div[2]/div/ul/li"
    APARTMENT_BOX_XPATH = "/html/body/div[2]/div[4]/div[2]/div/div[2]/div/div[2]/div[1]/div[1]/form/div/div[5]/div/div"
    APARTMENT_BOXLIST_XPATH = "/html/body/div[2]/div[4]/div[2]/div/div[2]/div/div[2]/div[1]/div[1]/form/div/div[5]/div/div[2]/div/ul/li"
    main()
