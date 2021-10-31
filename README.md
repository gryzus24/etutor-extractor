# etutor-extractor
Program do szybkiego eksportowania powtórek z serwisu www.etutor.pl.

## Instalacja
- Pobieramy .zip (Windows) lub .tar.gz (Posix)
- Rozpakowujemy
- Instalujemy Pythona >= 3.7 (https://www.python.org/downloads/)
- Otwieramy terminal i instalujemy wymagane biblioteki:<br>
  `pip install requests beautifulsoup lxml`

## Użycie
- Przechodzimy do folderu ze skryptem
- Możemy zmienić ustawienia eksportowania edytując plik "config.txt"
- Otwieramy za pomocą Pythona:<br>
  `python etutor_extractor.py` lub `python3 etutor_extractor.py`
- Logujemy się do eTutora
- Pobrane powtórki zapisane zostaną do pliku "karty.txt"

## Dlaczego?
eTutor jest serwisem płatnym, który w dużej części opiera swoje działanie na dodawaniu powtórek ze słownika diki.pl.  Mając to na uwadze, serwis nie udostępnia użytkownikowi łatwo dostępnej opcji eksportowania dodanych powtórek - opcja ta miałaby wymiar czysto praktyczny, jako iż większość informacji o powtórkach jest dostępna dla użytkownika.
