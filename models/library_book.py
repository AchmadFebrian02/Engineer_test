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
    isbn = fields.Char(string='ISBN')
    publication_year = fields.Integer(string='Publication Year')

