"""Support for Coinbase sensors."""
import logging

from homeassistant.components.sensor import (
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL,
    SensorEntity,
)
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    API_ACCOUNT_AMOUNT,
    API_ACCOUNT_BALANCE,
    API_ACCOUNT_CURRENCY,
    API_ACCOUNT_ID,
    API_ACCOUNT_NAME,
    API_ACCOUNT_NATIVE_BALANCE,
    API_RATES,
    API_RESOURCE_TYPE,
    API_TYPE_VAULT,
    CONF_CURRENCIES,
    CONF_EXCHANGE_RATES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

ATTR_NATIVE_BALANCE = "Balance in native currency"

CURRENCY_ICONS = {
    "BTC": "mdi:currency-btc",
    "ETH": "mdi:currency-eth",
    "EUR": "mdi:currency-eur",
    "LTC": "mdi:litecoin",
    "USD": "mdi:currency-usd",
}

DEFAULT_COIN_ICON = "mdi:cash"

ATTRIBUTION = "Data provided by coinbase.com"


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Coinbase sensor platform."""
    instance = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    provided_currencies = [
        account[API_ACCOUNT_CURRENCY]
        for account in instance.accounts
        if account[API_RESOURCE_TYPE] != API_TYPE_VAULT
    ]

    desired_currencies = []

    if CONF_CURRENCIES in config_entry.options:
        desired_currencies = config_entry.options[CONF_CURRENCIES]

    exchange_base_currency = instance.exchange_rates[API_ACCOUNT_CURRENCY]

    for currency in desired_currencies:
        if currency not in provided_currencies:
            _LOGGER.warning(
                "The currency %s is no longer provided by your account, please check "
                "your settings in Coinbase's developer tools",
                currency,
            )
            continue
        entities.append(AccountSensor(instance, currency))

    if CONF_EXCHANGE_RATES in config_entry.options:
        for rate in config_entry.options[CONF_EXCHANGE_RATES]:
            entities.append(
                ExchangeRateSensor(
                    instance,
                    rate,
                    exchange_base_currency,
                )
            )

    async_add_entities(entities)


class AccountSensor(SensorEntity):
    """Representation of a Coinbase.com sensor."""

    def __init__(self, coinbase_data, currency):
        """Initialize the sensor."""
        self._coinbase_data = coinbase_data
        self._currency = currency
        for account in coinbase_data.accounts:
            if (
                account[API_ACCOUNT_CURRENCY] == currency
                and account[API_RESOURCE_TYPE] != API_TYPE_VAULT
            ):
                self._name = f"Coinbase {account[API_ACCOUNT_NAME]}"
                self._id = (
                    f"coinbase-{account[API_ACCOUNT_ID]}-wallet-"
                    f"{account[API_ACCOUNT_CURRENCY]}"
                )
                self._state = account[API_ACCOUNT_BALANCE][API_ACCOUNT_AMOUNT]
                self._unit_of_measurement = account[API_ACCOUNT_CURRENCY]
                self._native_balance = account[API_ACCOUNT_NATIVE_BALANCE][
                    API_ACCOUNT_AMOUNT
                ]
                self._native_currency = account[API_ACCOUNT_NATIVE_BALANCE][
                    API_ACCOUNT_CURRENCY
                ]
                break
        self._attr_state_class = STATE_CLASS_TOTAL
        self._attr_device_info = DeviceInfo(
            configuration_url="https://www.coinbase.com/settings/api",
            entry_type="service",
            identifiers={(DOMAIN, self._coinbase_data.user_id)},
            manufacturer="Coinbase.com",
            name=f"Coinbase {self._coinbase_data.user_id[-4:]}",
        )

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return the Unique ID of the sensor."""
        return self._id

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement this sensor expresses itself in."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return CURRENCY_ICONS.get(self._unit_of_measurement, DEFAULT_COIN_ICON)

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            ATTR_NATIVE_BALANCE: f"{self._native_balance} {self._native_currency}",
        }

    def update(self):
        """Get the latest state of the sensor."""
        self._coinbase_data.update()
        for account in self._coinbase_data.accounts:
            if (
                account[API_ACCOUNT_CURRENCY] == self._currency
                and account[API_RESOURCE_TYPE] != API_TYPE_VAULT
            ):
                self._state = account[API_ACCOUNT_BALANCE][API_ACCOUNT_AMOUNT]
                self._native_balance = account[API_ACCOUNT_NATIVE_BALANCE][
                    API_ACCOUNT_AMOUNT
                ]
                self._native_currency = account[API_ACCOUNT_NATIVE_BALANCE][
                    API_ACCOUNT_CURRENCY
                ]
                break


class ExchangeRateSensor(SensorEntity):
    """Representation of a Coinbase.com sensor."""

    def __init__(self, coinbase_data, exchange_currency, exchange_base):
        """Initialize the sensor."""
        self._coinbase_data = coinbase_data
        self.currency = exchange_currency
        self._name = f"{exchange_currency} Exchange Rate"
        self._id = f"coinbase-{coinbase_data.user_id}-xe-{exchange_currency}"
        self._state = round(
            1 / float(self._coinbase_data.exchange_rates[API_RATES][self.currency]), 2
        )
        self._unit_of_measurement = exchange_base
        self._attr_state_class = STATE_CLASS_MEASUREMENT
        self._attr_device_info = DeviceInfo(
            configuration_url="https://www.coinbase.com/settings/api",
            entry_type="service",
            identifiers={(DOMAIN, self._coinbase_data.user_id)},
            manufacturer="Coinbase.com",
            name=f"Coinbase {self._coinbase_data.user_id[-4:]}",
        )

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique ID of the sensor."""
        return self._id

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement this sensor expresses itself in."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return CURRENCY_ICONS.get(self.currency, DEFAULT_COIN_ICON)

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {ATTR_ATTRIBUTION: ATTRIBUTION}

    def update(self):
        """Get the latest state of the sensor."""
        self._coinbase_data.update()
        self._state = round(
            1 / float(self._coinbase_data.exchange_rates.rates[self.currency]), 2
        )
