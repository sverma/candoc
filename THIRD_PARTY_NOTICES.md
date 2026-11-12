# Third-party notices

Country and currency reference data in `backend/app/countries.py` is derived from the ISO data distributed in pycountry 26.2.16, obtained from the official PyPI package. The data is bundled locally so the application does not send profile information to a country-lookup service.

The pycountry package is distributed under LGPL-2.1-only and carries ISO-data copyright notices. See [copyright notices](docs/licenses/pycountry-COPYRIGHT.txt) and [license text](docs/licenses/pycountry-LGPL-2.1.txt). The bundled data remains subject to its applicable terms; Candoc application code is MIT licensed. The complete editable derived catalog is supplied in the repository and can be replaced. The original source distribution is available from [pycountry 26.2.16](https://pypi.org/project/pycountry/26.2.16/#files).

Other dependencies retain their respective licenses as specified by their distributions and lockfiles.
