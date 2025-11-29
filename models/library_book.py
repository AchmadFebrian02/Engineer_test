from odoo import models, fields, api
from odoo.exceptions import ValidationError

class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'

    name = fields.Char(string='Title', required=True)
    author = fields.Char(string='Author')
    price = fields.Float(string='Price', default=0.0)
    category = fields.Selection([
        ('education', 'Education'),
        ('novel', 'Novel'),
        ('science', 'Science'),
        ('technology', 'Technology'),
        ('history', 'History'),
    ], string='Category')

    @api.constrains('price')
    def _check_price_non_negative(self):
        for record in self:
            if record.price < 0:
                raise ValidationError("Price must be non-negative.")
            
    def action_count_books_by_category(self):
        result = self.read_group(
            [('category', '!=', False)],
            ['category', 'category_count:count(id)'],
            ['category']
        )

        msg = ""
        for r in result:
            msg += f"{r['category']} : {r['category_count']} books\n"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Books per Category',
                'message': msg,
                'sticky': False,
            }
        }
    def action_fetch_openlibrary_data(self):
        """Fetch book metadata from OpenLibrary using the record's ISBN.

        - If ISBN is missing show a notification asking the user to fill it.
        - Attempts to fetch the JSON from https://openlibrary.org/isbn/<isbn>.json
        - Updates `name` (title), `author` and `publication_year` if available.
        Returns a client action that displays a notification (success or error).
        """
        self.ensure_one()
        if not self.isbn:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Missing ISBN',
                    'message': 'Please enter an ISBN before fetching data.',
                    'sticky': False,
                }
            }

        url = f'https://openlibrary.org/isbn/{self.isbn}.json'
        try:
            try:
                import requests
                r = requests.get(url, timeout=6)
                r.raise_for_status()
                data = r.json()
            except Exception:
                from urllib.request import urlopen
                import json
                with urlopen(url, timeout=6) as f:
                    data = json.load(f)

            title = data.get('title')
            if title:
                self.name = title

            authors = data.get('authors') or []
            if authors:
                names = []
                for a in authors:
                    if isinstance(a, dict) and a.get('name'):
                        names.append(a.get('name'))
                    else:
                        names.append(str(a.get('key') or a))
                self.author = ', '.join(names)
            publish_date = data.get('publish_date')
            if publish_date:
                import re
                m = re.search(r"(\d{4})", str(publish_date))
                if m:
                    try:
                        self.publication_year = int(m.group(1))
                    except Exception:
                        pass

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'OpenLibrary: OK',
                    'message': 'Book metadata was fetched and updated (if available).',
                    'sticky': False,
                }
            }

        except Exception as exc:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'OpenLibrary: Error',
                    'message': f'Failed to fetch data for ISBN {self.isbn}: {exc}',
                    'sticky': True,
                }
            }
    
    def action_fetch_openlibrary_data(self):
        """Fetch data from OpenLibrary.org using the record ISBN.

        Called by a form button. For each selected record the method:
        - validates that an ISBN is present
        - fetches https://openlibrary.org/isbn/<isbn>.json
        - updates the name (title), author and publication_year when available
        - returns an in-app notification describing the result

        This implementation uses the stdlib urllib so it doesn't depend on third
        party packages being installed in the environment.
        """
        import json
        from urllib.request import urlopen, Request
        from urllib.error import HTTPError, URLError

        notifications = []
        for book in self:
            if not book.isbn:
                notifications.append(f"{book.display_name}: missing ISBN.")
                continue

            url = f"https://openlibrary.org/isbn/{book.isbn}.json"
            try:
                req = Request(url, headers={"User-Agent": "Odoo-LibraryBook/1.0"})
                with urlopen(req, timeout=10) as resp:
                    data = json.load(resp)
            except HTTPError as e:
                notifications.append(f"{book.display_name}: ISBN not found ({e.code}).")
                continue
            except URLError as e:
                notifications.append(f"{book.display_name}: network error ({e}).")
                continue
            except Exception as e:
                notifications.append(f"{book.display_name}: failed to fetch ({e}).")
                continue

            vals = {}
            # Title
            title = data.get("title")
            if title:
                vals['name'] = title

            authors = data.get('authors')
            if authors:
                names = []
                for a in authors:
                    if isinstance(a, dict) and a.get('name'):
                        names.append(a['name'])
                if names:
                    vals['author'] = ', '.join(names)
            pub_year = None
            if 'publish_year' in data and isinstance(data.get('publish_year'), list) and data.get('publish_year'):
                try:
                    pub_year = int(data['publish_year'][0])
                except Exception:
                    pub_year = None
            elif 'publish_date' in data and isinstance(data.get('publish_date'), str):
                import re
                m = re.search(r"(\d{4})", data['publish_date'])
                if m:
                    try:
                        pub_year = int(m.group(1))
                    except Exception:
                        pub_year = None

            if pub_year:
                vals['publication_year'] = pub_year

            if vals:
                try:
                    book.write(vals)
                    notifications.append(f"{book.display_name}: updated ({', '.join(list(vals.keys()))}).")
                except Exception as e:
                    notifications.append(f"{book.display_name}: failed to update ({e}).")
            else:
                notifications.append(f"{book.display_name}: no usable data found.")
                
        message = '\n'.join(notifications) or 'No records processed.'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'OpenLibrary fetch',
                'message': message,
                'sticky': False,
            }
        }
    isbn = fields.Char(string='ISBN')
    publication_year = fields.Integer(string='Publication Year')

