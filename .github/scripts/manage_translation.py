#!/usr/bin/env python
#
# This python file contains utility scripts to manage Python docs Ukrainian translation.
# It has to be run inside the python-docs-uk git root directory.
#
# Inspired by django-docs-translations script by claudep.
#
# The following commands are available:
#
# * fetch: fetch translations from transifex.com and strip source lines from the
#          files.
# * recreate_readme: recreate readme to update translation progress.
# * regenerate_tx_config: recreate configuration for all resources.

from argparse import ArgumentParser
from collections import Counter
import os
from re import match
from subprocess import call, run
import sys

LANGUAGE = 'uk'
RESOURCE_NAME_MAP = {'glossary_': 'glossary'}
TX_ORGANISATION = 'python-doc'
TX_PROJECT = 'python-newest'
GH_ORGANISATION = 'python'
GH_PROJECT = 'python-docs-uk'

def fetch():
    """
    Fetch translations from Transifex, remove source lines.
    """
    if call("tx --version", shell=True) != 0:
        sys.stderr.write("The Transifex client app is required (https://developers.transifex.com/docs/cli).\n")
        exit(1)
    lang = LANGUAGE
    pull_returncode = call(f'tx pull -l {lang} --minimum-perc=1 --force --skip', shell=True)
    if pull_returncode != 0:
        exit(pull_returncode)
    for root, _, po_files in os.walk('../..'):
        for po_file in po_files:
            if not po_file.endswith(".po"):
                continue
            po_path = os.path.join(root, po_file)
            call(f'msgcat --no-location -o {po_path} {po_path}', shell=True)


def recreate_tx_config():
    """
    Regenerate Transifex client config for all resources.
    """
    resources = _get_resources()
    with open('.tx/config', 'w') as config:
        config.writelines(('[main]\n', 'host = https://www.transifex.com\n',))
        for resource in resources:
            slug = resource['slug']
            name = RESOURCE_NAME_MAP.get(slug, slug)
            if slug == '0':
                continue
            elif '--' in slug:
                directory, file_name = name.split('--')
                if match(r'\d+_\d+', file_name):
                    file_name = file_name.replace('_', '.')
                config.writelines(
                    (
                        '\n',
                        f'[{TX_PROJECT}.{slug}]\n',
                        f'trans.{LANGUAGE} = {directory}/{file_name}.po\n',
                        'type = PO\n',
                        'source_lang = en\n',
                    )
                )
            else:
                config.writelines(
                    (
                        '\n',
                        f'[{TX_PROJECT}.{slug}]\n',
                        f'trans.{LANGUAGE} = {name}.po\n',
                        'type = PO\n',
                        'source_lang = en\n',
                    )
                )


def _get_resources():
    from requests import get

    resources = []
    offset = 0
    if os.path.exists('.tx/api-key'):
        with open('.tx/api-key') as f:
            transifex_api_key = f.read()
    else:
        transifex_api_key = os.getenv('TX_TOKEN')
    while True:
        response = get(
            f'https://api.transifex.com/organizations/{TX_ORGANISATION}/projects/{TX_PROJECT}/resources/',
            params={'language_code': LANGUAGE, 'offset': offset},
            auth=('api', transifex_api_key),
        )
        response.raise_for_status()
        response_list = response.json()
        resources.extend(response_list)
        if len(response_list) < 100:
            break
        offset += len(response_list)
    return resources


def _get_unique_translators():
    process = run(
        ['grep', '-ohP', r'(?<=^# )(.+)(?=, \d+$)', '-r', '.'],
        capture_output=True,
        text=True,
    )
    translators = [match('(.*)( <.*>)?', t).group(1) for t in process.stdout.splitlines()]
    unique_translators = Counter(translators)
    return unique_translators


def recreate_readme():
    def language_switcher(entry):
        return (
            entry['name'].startswith('bugs')
            or entry['name'].startswith('tutorial')
            or entry['name'].startswith('library--functions')
        )

    def average(averages, weights):
        return sum([a * w for a, w in zip(averages, weights)]) / sum(weights)

    resources = _get_resources()
    filtered = list(filter(language_switcher, resources))
    average_list = [e['stats']['translated']['percentage'] for e in filtered]
    weights_list = [e['wordcount'] for e in filtered]

    language_switcher_status = average(average_list, weights=weights_list) * 100
    unique_translators = _get_unique_translators()
    number_of_translators = len(unique_translators)

    with open('README.md', 'w') as file:
        file.write(
            f'''\
Український переклад документації Python
========================================
![build](https://github.com/{GH_ORGANISATION}/{GH_PROJECT}/workflows/.github/workflows/update-and-build.yml/badge.svg)
![{language_switcher_status:.2f}% прогрес перекладу](https://img.shields.io/badge/прогрес_перекладу-{language_switcher_status:.2f}%25-0.svg)
![хід перекладу всієї документації](https://img.shields.io/badge/dynamic/json.svg?label=всього&query=$.{LANGUAGE}&url=http://gce.zhsj.me/python/newest)
![{number_of_translators} перекладачів](https://img.shields.io/badge/перекладачів-{number_of_translators}-0.svg)

Якщо ви знайшли помилку або маєте пропозицію,
[додати issue](https://github.com/{GH_ORGANISATION}/{GH_PROJECT}/issues) у цьому проекті або запропонуйте зміни:

* Зареєструйтесь на платформі [Transifex](https://www.transifex.com/) 
* Перейдіть на сторінку [документації Python](https://www.transifex.com/{TX_ORGANISATION}/{TX_PROJECT}/).
* Натисніть кнопку „Join Team”, оберіть українську (uk) мову та натисніть „Join” щоб приєднатися до команди.
* Приєднавшись до команди, виберіть ресурс, що хочете виправити/оновити.

Додаткову інформацію про використання Transifex дивіться [в документації](https://docs.transifex.com/getting-started-1/translators).

**Прогрес перекладу**

![прогрес перекладу](language-switcher-progress.svg)

Українська мова з’явиться в меню вибору мови docs.python.org, [коли будуть повністю перекладені](https://www.python.org/dev/peps/pep-0545/#add-translation-to-the-language-switcher):
* `bugs`,
* всі ресурси в каталозі `tutorial`,
* `library/functions`.

**Як переглянути останню збірку документації?**

Завантажте останню створену документацію зі списку артефактів в останній дії GitHub (вкладка Actions).
Переклади завантажуються з Transifex до цього репозиторію приблизно кожні півгодини.
Документація на python.org оновлюється приблизно раз на день.

**Канали зв'язку**

* [Telegram-чат перекладачів](https://t.me/+dXwqHZ0KPKYyNDc6)
* [Python translations working group](https://mail.python.org/mailman3/lists/translation.python.org/)
* [Python Documentation Special Interest Group](https://www.python.org/community/sigs/current/doc-sig/)

**Ліцензія**

Запрошуючи вас до спільного створення проекту на платформі Transifex, ми пропонуємо договір на передачу ваших перекладів
Python Software Foundation [по ліцензії CC0](https://creativecommons.org/publicdomain/zero/1.0/deed.uk).
Натомість ви побачите, що ви є перекладачем тієї частини, яку ви переклали.
Ви висловлюєте свою згоду з цією угодою, надаючи свою роботу для включення в документацію.

**Оновлення локального перекладу**

* `.github/scripts/manage_translation.py recreate_tx_config`
* `.github/scripts/manage_translation.py fetch`
* `.github/scripts/manage_translation.py recreate_readme`

**Подяка**
* Maciej Olko - Polish team
* Julien Palard - French team
* Tomo Cocoa - Japanese team

**Внесок спільноти**  

| Перекладач      | Кількість документів |  
|:----------------|:--------------------:|  
'''
        )

        file.writelines(
            (f'|{t}|{c}|\n' for (t, c) in unique_translators.most_common())
        )


if __name__ == "__main__":
    RUNNABLE_SCRIPTS = ('fetch', 'recreate_tx_config', 'recreate_readme')

    parser = ArgumentParser()
    parser.add_argument('cmd', nargs=1, choices=RUNNABLE_SCRIPTS)
    options = parser.parse_args()

    eval(options.cmd[0])()
