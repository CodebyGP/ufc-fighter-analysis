from flask import Flask, render_template, request, jsonify
import re
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

def format_time(seconds):
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes} min {seconds:02d} sec"

# Format percentages and remove ".0"
def floatformat_custom(value):
    if value is None:
        return None
    return "{:.0%}".format(value / 100)

app.jinja_env.filters['format_time'] = format_time
app.jinja_env.filters['floatformat_custom'] = floatformat_custom

def extract_numerical_value(text):
    if text is None:
        return None
    match = re.search(r'[\d.]+', text)
    if match:
        return float(match.group())
    else:
        return None

def convert_time_to_seconds(time_str):
    if time_str is None:
        return None
    parts = time_str.split(":")
    if len(parts) == 2:
        minutes = int(parts[0])
        seconds = int(parts[1])
        return minutes * 60 + seconds
    return None

def get_stats_by_name(name):
    base_url = "https://www.ufc.com/athlete/"
    full_url = base_url + name.lower().replace(" ", "-")
    fighter_stats = extract_fighter_stats(full_url)
    return fighter_stats

def get_fighter_image_url(fighter_name):
    formatted_name = fighter_name.lower().replace(" ", "-")
    base_url = f"https://www.ufc.com/athlete/{formatted_name}"
    response = requests.get(base_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        img_tag = soup.find("div", class_="hero-profile__image-wrap").find("img")
        if img_tag and "src" in img_tag.attrs:
            return img_tag['src']
    return None

def calculate_fighter_advantages(stats1, stats2):
    excluded_stats = ['fighter_name', 'age', 'fighter_birth', 'weight_class'] 
    fighter_advantages = []

    for stat in stats1:
        if stat in excluded_stats:
            continue

        if stat in stats2: 
            if isinstance(stats1[stat], (int, float)) and isinstance(stats2[stat], (int, float)):
                difference = abs(stats1[stat] - stats2[stat])
                if stats1[stat] > stats2[stat]:
                    advantage = stats1['fighter_name']
                elif stats1[stat] < stats2[stat]:
                    advantage = stats2['fighter_name']
                else:
                    advantage = "Equal"

                fighter_advantages.append({'stat': stat, 'advantage': advantage, 'difference': difference})

    return fighter_advantages

#Scrapes UFC website for rankings
def scrape_rankings(RANKINGS):
    response = requests.get("https://www.ufc.com/rankings")
    ufc_webpage = response.text
    soup = BeautifulSoup(ufc_webpage, "html.parser")

    AMOUNT_OF_RANKINGS = 16

    rankings_dict = {}

    weight_classes = [
        ("Pound-for-Pound", 1),
        ("Flyweight", 2),
        ("Bantamweight", 3),
        ("Featherweight", 4),
        ("Lightweight", 5),
        ("Welterweight", 6),
        ("Middleweight", 7),
        ("Light Heavyweight", 8),
        ("Heavyweight", 9),
        ("Women's Pound-for-Pound", 10),
        ("Women's Strawweight", 11),
        ("Women's Flyweight", 12),
        ("Women's Bantamweight", 13)
    ]

    for weight_class, limit in weight_classes:
        fighters = soup.find_all(name="a", hreflang="en", limit=(AMOUNT_OF_RANKINGS * limit))
        fighter_list = [fighter.getText() for fighter in fighters][(AMOUNT_OF_RANKINGS * (limit - 1)):]
        if weight_class == "Women's Bantamweight":
            if "Champion" not in fighter_list[0]:
                fighter_list.insert(0, "Champion N/A")
        rankings_dict[weight_class] = combine_rankings(RANKINGS, fighter_list)

    return rankings_dict

def combine_rankings(RANKINGS, fighter_list):
    combined_rankings = []

    for i, fighter in enumerate(fighter_list):
        if i == 0:
            # Handle the case of the top fighter as "Champion"
            combined_rankings.append("Champion: " + fighter)
        else:
            # Skip the ranking number and add the fighter's name
            fighter_name = fighter.split(". ", 1)[-1]
            combined_rankings.append(str(i) + ". " + fighter_name)

    return '\n'.join(combined_rankings)


@app.route('/', methods=['GET', 'POST'])
def index():
    fighter_stats = [None, None]
    fighter_image_urls = [None, None]
    fighter_advantages = []
    error_message = None
    rankings_dict ={}

    if request.method == 'POST':
        fighter_names = [request.form['fighter_name1'], request.form['fighter_name2']]


        for i, fighter_name in enumerate(fighter_names):
            fighter_stats[i] = get_stats_by_name(fighter_name)
            if fighter_stats[i] is None:
                error_message = f"{fighter_name} is either misspelled or is not a UFC fighter, try again!"
                break #Stop if fighter is not found
            fighter_image_urls[i] = get_fighter_image_url(fighter_name)
        
        if error_message is None:
            fighter_advantages = calculate_fighter_advantages(fighter_stats[0], fighter_stats[1])

        RANKINGS = ['1. ', '2. ', '3. ', '4. ', '5. ', '6. ', '7. ', '8. ', '9. ', '10. ', '11. ', '12. ', '13. ', '14. ', '15. ']
        rankings_dict = scrape_rankings(RANKINGS)

    return render_template('templates.html', fighter_stats=fighter_stats, 
                                            fighter_image_urls=fighter_image_urls, 
                                            fighter_advantages=fighter_advantages,
                                            error_message = error_message,
                                            rankings_dict = rankings_dict)

@app.route('/rankings')
def rankings():
    RANKINGS = ['1. ', '2. ', '3. ', '4. ', '5. ', '6. ', '7. ', '8. ', '9. ', '10. ', '11. ', '12. ', '13. ', '14. ', '15. ']
    rankings_dict = scrape_rankings(RANKINGS)
    return render_template('rankings.html', rankings_dict=rankings_dict)

#Scraps Fighter data and organizes them appropriately
def extract_fighter_stats(fighter_url):
    response = requests.get(fighter_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        fighter_name = soup.find(class_='hero-profile__name').get_text()
        age = int(soup.find(class_='field field--name-age field--type-integer field--label-hidden field__item').get_text(strip=True))
        fighter_birth =soup.find(class_='c-bio__label', text='Place of Birth').find_next(class_='c-bio__text').get_text(strip=True)
        reach = float(soup.find(class_='c-bio__label', text='Reach').find_next(class_='c-bio__text').get_text(strip=True))
        height = float(soup.find(class_='c-bio__label', text='Height').find_next(class_='c-bio__text').get_text(strip=True))
        weight_class = soup.find(class_="hero-profile__division-title").get_text(strip=True)
        striking_accuracy = soup.find(text=re.compile(r'Striking accuracy'))
        takedown_accuracy = soup.find(text=re.compile(r'Takedown Accuracy'))
        takedown_defense = soup.find("div", class_="c-stat-compare__label", text="Takedown Defense").find_previous_sibling("div", class_="c-stat-compare__number").get_text(strip=True)
        takedown_avg = soup.find("div", class_="c-stat-compare__label", text="Takedown avg").find_previous_sibling("div", class_="c-stat-compare__number").get_text(strip=True)
        sig_str_defense = soup.find("div", class_="c-stat-compare__label", text="Sig. Str. Defense").find_previous_sibling("div", class_="c-stat-compare__number").get_text(strip=True)
        sig_str_landed = soup.find(class_= 'c-stat-compare__number').get_text(strip=True)
        avg_fight_time = soup.find("div", class_="c-stat-compare__label", text="Average fight time").find_previous_sibling("div", class_="c-stat-compare__number").get_text(strip=True)

        striking_accuracy = extract_numerical_value(striking_accuracy)
        takedown_accuracy = extract_numerical_value(takedown_accuracy)
        takedown_defense = extract_numerical_value(takedown_defense)
        takedown_avg = extract_numerical_value(takedown_avg)
        sig_str_defense = extract_numerical_value(sig_str_defense)
        sig_str_landed = extract_numerical_value(sig_str_landed)
        avg_fight_time = avg_fight_time

        # Return the extracted stats as a dictionary
        fighter_stats =  {
            'fighter_name': fighter_name,
            'age': age,
            'fighter_birth': fighter_birth,
            'Reach': reach,
            'Height':height,
            'weight_class': weight_class,
            'Striking Accuracy': striking_accuracy,
            'Takedown Accuracy': takedown_accuracy,
            'Takedown Defense': takedown_defense,
            'Takedown Avg': takedown_avg,
            'Sig Str Defense': sig_str_defense,
            'Sig Str Landed': sig_str_landed,
            'Avg Fight Time': avg_fight_time,
        }
        return fighter_stats
    else:
        print(f"Failed to retrieve fighter stats for {fighter_url}")
        return None

if __name__ == '__main__':
    app.run(debug=True)