# Compania de Apa Arad pentru Home Assistant

<p align="center">
  <img src="images/logo.png" alt="Compania de Apa Arad" width="160">
</p>

Integrare custom pentru Home Assistant care se autentifica in portalul Compania de Apa Arad si expune informatii gasite in cont.

## Instalare prin HACS

1. In Home Assistant, deschide HACS.
2. Mergi la `Integrations` -> meniul cu trei puncte -> `Custom repositories`.
3. Adauga repository-ul:

   ```text
   https://github.com/gonzolicu/ha-apa-arad
   ```

4. Alege categoria `Integration`.
5. Instaleaza integrarea si reporneste Home Assistant.
6. Mergi la `Settings` -> `Devices & services` -> `Add integration` si cauta `Compania de Apa Arad`.

## Entitati

Integrarea poate crea senzori pentru status, sold, ultima factura, consum si numar contor, plus un buton pentru actualizare manuala.

Valorile sunt extrase din pagina web a portalului, deci pot necesita ajustari daca portalul isi schimba structura HTML.
