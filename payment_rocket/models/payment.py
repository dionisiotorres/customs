# -*- coding: utf-8 -*-

from eagle import api, fields, models, _
from eagle.addons.payment.models.payment_acquirer import ValidationError
from eagle.tools.float_utils import float_compare

import logging
import pprint

_logger = logging.getLogger(__name__)


class RocketPaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('rocket', 'Rocket')], default='transfer')

    @api.model
    def _create_missing_journal_for_acquirers(self, company=None):
        # By default, the wire transfer method uses the default Bank journal.
        company = company or self.env.user.company_id
        acquirers = self.env['payment.acquirer'].search(
            [('provider', '=', 'rocket'), ('journal_id', '=', False), ('company_id', '=', company.id)])

        bank_journal = self.env['account.journal'].search(
            [('type', '=', 'bank'), ('company_id', '=', company.id)], limit=1)
        if bank_journal:
            acquirers.write({'journal_id': bank_journal.id})
        return super(RocketPaymentAcquirer, self)._create_missing_journal_for_acquirers(company=company)

    def rocket_get_form_action_url(self):
        return '/payment/rocket/info'

    def _format_rocket_data(self):
        company_id = self.env.user.company_id.id
        # filter only bank accounts marked as visible
        journals = self.env['account.journal'].search([('type', '=', 'bank'), ('company_id', '=', company_id)])
        accounts = journals.mapped('bank_account_id').name_get()
        bank_title = _('Bank Accounts') if len(accounts) > 1 else _('Bank Account')
        bank_accounts = ''.join(['<ul>'] + ['<li>%s</li>' % name for id, name in accounts] + ['</ul>'])
        post_msg = _('''<div>
<h3>Please use the following transfer details</h3>
<h4>%(bank_title)s</h4>
%(bank_accounts)s
<h4>Communication</h4>
<p>Please use the order name as communication reference.</p>
</div>''') % {
            'bank_title': bank_title,
            'bank_accounts': bank_accounts,
        }
        return post_msg

    @api.model
    def create(self, values):
        """ Hook in create to create a default post_msg. This is done in create
        to have access to the name and other creation values. If no post_msg
        or a void post_msg is given at creation, generate a default one. """
        if values.get('provider') == 'rocket' and not values.get('post_msg'):
            values['post_msg'] = self._format_rocket_data()
        return super(RocketPaymentAcquirer, self).create(values)

    @api.multi
    def write(self, values):
        """ Hook in write to create a default post_msg. See create(). """
        if all(not acquirer.post_msg and acquirer.provider != 'rocket' for acquirer in self) and values.get('provider') == 'rocket':
            values['post_msg'] = self._format_rocket_data()
        return super(RocketPaymentAcquirer, self).write(values)


class rocketPaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _rocket_form_get_tx_from_data(self, data):
        reference, amount, currency_name = data.get('reference'), data.get('amount'), data.get('currency_name')
        tx = self.search([('reference', '=', reference)])

        if not tx or len(tx) > 1:
            error_msg = _('received data for reference %s') % (pprint.pformat(reference))
            if not tx:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        return tx

    def _rocket_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        if float_compare(float(data.get('amount', '0.0')), self.amount, 2) != 0:
            invalid_parameters.append(('amount', data.get('amount'), '%.2f' % self.amount))
        if data.get('currency') != self.currency_id.name:
            invalid_parameters.append(('currency', data.get('currency'), self.currency_id.name))

        return invalid_parameters

    def _rocket_form_validate(self, data):
        _logger.info('Validated Rocket payment for tx %s: set as pending' % (self.reference))
        self._set_transaction_pending()
        return True
