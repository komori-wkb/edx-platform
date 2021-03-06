# -*- coding: utf-8 -*-
import re

from django import forms
from django.utils.translation import ugettext as _, get_language

from .models import PersonalInfo


class PersonalInfoModelForm(forms.ModelForm):
    full_name = forms.CharField()
    kana = forms.CharField()
    postal_code = forms.CharField(max_length=7, min_length=7,
                                  widget=forms.TextInput(attrs={'class': 'postal_code_field'}))
    address_line_1 = forms.CharField()
    address_line_2 = forms.CharField(required=False)
    phone_number = forms.CharField()
    gaccatz_check = forms.BooleanField(widget=forms.CheckboxInput(attrs={'class': 'gaccatz_check_field'}))
    free_entry_field_1 = forms.CharField(widget=forms.Textarea())
    free_entry_field_2 = forms.CharField(widget=forms.Textarea())
    free_entry_field_3 = forms.CharField(widget=forms.Textarea())
    free_entry_field_4 = forms.CharField(widget=forms.Textarea())
    free_entry_field_5 = forms.CharField(widget=forms.Textarea())

    class Meta:
        model = PersonalInfo
        fields = [
            'full_name',
            'kana',
            'postal_code',
            'address_line_1',
            'address_line_2',
            'phone_number',
            'gaccatz_check',
            'free_entry_field_1',
            'free_entry_field_2',
            'free_entry_field_3',
            'free_entry_field_4',
            'free_entry_field_5',
        ]
        exclude = ['user', 'order', 'choice']

    def __init__(self, *args, **kwargs):
        personal_info_setting = kwargs.get('personal_info_setting')
        if personal_info_setting:
            del (kwargs['personal_info_setting'])
        super(PersonalInfoModelForm, self).__init__(*args, **kwargs)

        if not personal_info_setting.full_name:
            del (self.fields['full_name'])
        else:
            self.fields['full_name'].label = _('Full Name')
            self.fields['full_name'].widget = forms.TextInput(attrs={'placeholder': _('gacco taro')})

        if not personal_info_setting.kana or not get_language() in ['ja', 'ja-jp']:
            del (self.fields['kana'])
        else:
            self.fields['kana'].label = _('Kana')
            self.fields['kana'].widget = forms.TextInput(attrs={'placeholder': _(u'ガッコウ　タロウ')})

        if not personal_info_setting.postal_code:
            del (self.fields['postal_code'])
        else:
            self.fields['postal_code'].label = _('Postal/Zip Code')

        if not personal_info_setting.address_line_1:
            del (self.fields['address_line_1'])
        else:
            self.fields['address_line_1'].label = _('Address Line')
            self.fields['address_line_1'].widget = forms.TextInput(
                attrs={'placeholder': _('Urbannet Azabu Building 1-6-15 Minamiazabu'),
                       'class': 'address_line_1_field'})

        if not personal_info_setting.address_line_2:
            del (self.fields['address_line_2'])
        else:
            self.fields['address_line_2'].label = ''
            self.fields['address_line_2'].widget = forms.TextInput(
                attrs={'placeholder': _('Minato-Ku Tokyo Japan'),
                       'class': 'address_line_2_field'}
            )

        if not personal_info_setting.phone_number:
            del (self.fields['phone_number'])
        else:
            self.fields['phone_number'].label = _('Phone Number')
            self.fields['phone_number'].widget = forms.TextInput(
                attrs={'placeholder': _('0312345678 (Except Hyphen)')}
            )

        if not personal_info_setting.gaccatz_check:
            del (self.fields['gaccatz_check'])
        else:
            self.fields['gaccatz_check'].label = _(
                'We agree to the precondition for participation in gaccatz.')

        if not personal_info_setting.free_entry_field_1_title:
            del (self.fields['free_entry_field_1'])
        else:
            self.fields['free_entry_field_1'].label = personal_info_setting.free_entry_field_1_title

        if not personal_info_setting.free_entry_field_2_title:
            del (self.fields['free_entry_field_2'])
        else:
            self.fields['free_entry_field_2'].label = personal_info_setting.free_entry_field_2_title

        if not personal_info_setting.free_entry_field_3_title:
            del (self.fields['free_entry_field_3'])
        else:
            self.fields['free_entry_field_3'].label = personal_info_setting.free_entry_field_3_title

        if not personal_info_setting.free_entry_field_4_title:
            del (self.fields['free_entry_field_4'])
        else:
            self.fields['free_entry_field_4'].label = personal_info_setting.free_entry_field_4_title

        if not personal_info_setting.free_entry_field_5_title:
            del (self.fields['free_entry_field_5'])
        else:
            self.fields['free_entry_field_5'].label = personal_info_setting.free_entry_field_5_title

        # overwrite django default messages
        for field in self.fields.values():
            field.error_messages = {'required': _('The field is required.'), 'invalid': _("Enter a valid value.")}

    def clean_kana(self):
        kana = self.cleaned_data['kana']
        if not re.search(u'[ァ-ヴ 　][ァ-ヴー・]*$', kana):
            raise forms.ValidationError(_('Please type using full-width katakana and space.'))
        return kana

    @staticmethod
    def _check_number(value):
        if not re.match('^[0-9]*$', value):
            raise forms.ValidationError(_('Please type using half-width numbers.'))
        return value

    def clean_postal_code(self):
        postal_code = self.cleaned_data['postal_code']
        return self._check_number(postal_code)

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        return self._check_number(phone_number)
