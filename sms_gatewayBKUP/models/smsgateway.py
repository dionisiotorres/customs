import requests
from odoo import _,fields, models,api
import datetime

class SmsGatewayDevice(models.Model):
    _name='eagle.smsgateway.device'
    _description = "list of devices in the sms gateway Me Accounts"
    name=fields.Char("Device Name")
    sms_gateway=fields.Many2one("eagle.smsgateway",string="SMS Gateway")
    device_id=fields.Integer("Device Id")

class Message(models.Model):
    _name="eagle.smsgateway.message"
    message_id=fields.Integer("SMS ID",)
    device=fields.Many2one("eagle.smsgateway.device","From Device")
    device_id=fields.Integer("device Id",related="device.device_id")
    message=fields.Char("Message")
    phone_number=fields.Char("To")
    updated_at=fields.Datetime("Posted at")
    sent_at=fields.Datetime("Sent at")
    sms_status=fields.Selection([(1,"Pending"),
                                 (2,"Sent"),
                                 (3,"Failed")])
    created_at=fields.Datetime("created on",default=datetime.datetime.utcnow())
    _sql_constraints = [
        ('message_id_unique', 'unique(message_id)', 'Message Id Must Be Unique'),
    ]


    def send_sms(self):
        for rec in self:
            body = [{'device_id': rec.device_id,'phone_number':rec.phone_number,'message':rec.message}]
            response= rec.device.sms_gateway._make_post('message/send', body)
            rec.message_id=response[0]["id"]
            rec.updated_at=response[0]["updated_at"].replace('T'," ")
            if response[0]["status"]=='pending':
                rec.sms_status=1


        return response
    def get_sms(self):
        for rec in self:
            url = 'message/{}'.format(rec.message_id)
            response= rec.device.sms_gateway._make_get(url)
            if response["status"]=='sent':
                rec.sms_status=2
                rec.sent_at = response["updated_at"].replace('T', " ")
            if response["status"]=='failed':
                rec.sms_status=3
                rec.sent_at = response["updated_at"].replace('T', " ")
            return response
class SMSGateway(models.Model):
    # BASE_ENDPOINT = 'https://smsgateway.me/api/v4/'
    _name="eagle.smsgateway"
    name=fields.Char("SMS Gateway")
    base_endpoint=fields.Char("Base EndPoint")
    api_key=fields.Char("API Key")

    # def __init__(self, "api_key"):
    #     self.api_key = api_key

    def _get_headers(self):
        return {'Authorization': self.api_key}


    def _make_post(self,endpoint,body):
        url = self.base_endpoint + endpoint
        return requests.post(url, json=body, headers=self._get_headers()).json()
    def _make_get(self, endpoint):
        url = self.base_endpoint + endpoint
        return requests.get(url, headers=self._get_headers()).json()

    # def _make_post(self, endpoint, body):
    #     url = SMSGateway.BASE_ENDPOINT + endpoint
    #     return requests.post(url, json=body, headers=self._get_headers()).json()
    #
    # def search_devices(self, filters=None):
    #     return self._make_post('device/search', filters)
    #
    # def get_device(self, device_id):
    #     url = 'device/{}'.format(device_id)
    #     return self._make_get(url)
    #
    # def send_sms(self, *messages: Message):
    #     body = [m.__dict__ for m in messages]
    #     return self._make_post('message/send', body)
    #
    # def cancel_sms(self, *ids: int):
    #     body = [{'id': sms_id} for sms_id in ids]
    #     return self._make_post('message/cancel', body)
    #
    # def get_sms(self, sms_id: int):
    #     url = 'message/{}'.format(sms_id)
    #     return self._make_get(url)
    #
    # def search_sms(self, filters=None):
    #     return self._make_post('message/search', filters)
