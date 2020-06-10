"""Transformer for Home assistant."""
# import asyncio
from ..device import Device


def _subscribe_topic(item: dict) -> tuple:
    return (item["full"], 0)


def _get_topic_value(output_topic, data):
    value = list(
        filter(lambda item: item["tuya_value"] == data, output_topic["values"],)
    )
    return value[0]["default_value"]


class TransformDataPoint:
    """Transform DataPoint."""

    def __init__(self, main, device_key: str, data_point: dict):
        """Initialize TransformDataPoint."""
        self._main = main
        self._is_valid = False
        self._device_key = device_key
        self._dp_key = data_point["key"]
        self._command_value = None
        self.data_point = data_point
        self.component_config = None
        self.homeassistant_config = None

    async def update_config(self):
        """Get the config from main once available."""
        self.homeassistant_config = await self._main.get_ha_config(
            self._device_key, self._dp_key
        )
        print(self._device_key, self._dp_key)
        self.component_config = await self._main.get_ha_component(
            self.data_point["device_component"]
        )
        self.is_valid()

    def set_homeassistant_config(self, config):
        """Set the Home Assistant datapoint config."""
        self.homeassistant_config = config
        self.is_valid()

    def get_component_name(self) -> str:
        """Return the data point component name."""
        if not self.data_point:
            return "not_initialized"
        return self.data_point["device_component"]

    def set_component_config(self, config):
        """Set the Home Assistant variable model for datapoint."""
        self.component_config = config
        self.is_valid()

    def is_valid(self) -> bool:
        """Check if all configurations are valid and sane."""
        # TODO: check sane/valid homeassistant_config
        if self.homeassistant_config is None:
            return self._is_valid
        # TODO: check sane/valid component_config
        if self.component_config is None:
            return self._is_valid
        # TODO: check is_valid device
        self._is_valid = True
        return self._is_valid

    def set_data(self, data: bytes):
        """Set value for command."""
        self._command_value = data.decode("utf-8")

    def get_gateway_payload(self):
        """Get payload in gateway format."""
        command_topic_list = list(
            filter(
                lambda item: "publish_topic" in item
                and item["publish_topic"] == self.data_point["device_topic"],
                self.component_config["topics"],
            )
        )
        if len(command_topic_list) == 0:
            return

        gw_value_list = list(
            filter(
                lambda item: item["default_value"] == self._command_value,
                command_topic_list[0]["values"],
            )
        )

        if len(gw_value_list) == 0:
            return
        return gw_value_list[0]["tuya_value"]

    def _full_topic(self, item: dict):

        full = item.replace("~", self.homeassistant_config["~"])
        return {
            "full": full,
            # "key": self._device_key,
            "dp_key": self._dp_key,
            "topic": item.replace("~", ""),
        }

    def _get_topics_by_type(self, topic_type: str) -> list:

        return list(
            filter(
                lambda item: item["topic_type"] == topic_type,
                self.component_config["topics"].items(),
            )
        )

    def _get_topic_by_type_and_name(self, topic_type: str, name: str) -> dict:

        filtered = list(
            filter(
                lambda item: item["topic_type"] == topic_type and item["name"] == name,
                self.component_config["topics"],
            )
        )
        return filtered[0]

    def get_subscribe_topics(self) -> dict:
        """Get the topics to subscribe to for the datapoint."""
        # TODO: get list of possible subscribe topics
        # TODO: check which topics are in ha_config and yield
        for key, item in self.homeassistant_config.items():
            if key in ["cmd_t"]:
                yield _subscribe_topic(self._full_topic(item))

    def get_publish_topics(self, filters=None) -> dict:
        """Get the topics to publish to for the datapoint."""
        self._get_topics_by_type("publish")
        # TODO: check which topics are in ha_config and yield
        for key, item in self.homeassistant_config.items():
            if key in ["stat_t", "avty_t"]:
                yield self._full_topic(item)

    # def _get_publish_topic(self, output_topic):

    #     publish_topics = self._get_topics_by_type("publish")
    #     print(publish_topics, self.homeassistant_config)
    #     ha_filtered = list(filter(lambda item: item[0] in publish_topics, self.homeassistant_config.items()))
    #     print(ha_filtered)

    def get_publish_content(self, output_topic: str = "state", data=None):
        """Get the topic and ha payload."""
        # TODO: check if output_topic in homeassistant_config
        # self._get_publish_topic(output_topic)

        output_topic_dict = self._get_topic_by_type_and_name(
            "publish", f"{output_topic}_topic"
        )

        topic = self._full_topic(output_topic_dict["default_value"])["full"]
        payload = _get_topic_value(output_topic_dict, data)
        yield {"topic": topic, "payload": payload}


class Transform:
    """Transform Home Assistant I/O data."""

    def __init__(self, main, device: Device):
        """Initialize transform."""
        # TODO: remove device dependency, bad design
        # TODO: importing main might not be the best idea
        self._main = main
        self._device = device
        self._device_config = self._device.get_config()
        self._data_points = {}
        self._is_valid = False
        self._component_config = None
        self._homeassistant_config = None

        if (
            not self._device_config
            or self._device_config["topic_config"]
            or not self._device.is_valid()
        ):
            return
        for dp_value in self._device_config["dps"]:
            self._data_points[dp_value["key"]] = TransformDataPoint(
                self._main, self._device.key, dp_value
            )
        # self._is_valid = True

    def set_homeassistant_config(self, idx, ha_dict):
        """Pass the HA config to datapoint."""
        if idx in self._data_points:
            self._data_points[idx].set_homeassistant_config(ha_dict)

    def set_component_config(self, payload_dict: dict, component_name: str):
        """Pass the HA component config to datapoint."""
        for _, data_point in self._data_points.items():
            if data_point and component_name == data_point.get_component_name():
                data_point.set_component_config(payload_dict)

    async def update_config(self):
        """Trigger data points to pull the config."""
        # not the most efficient, but good enough for the task
        for _, dp_value in self._data_points.items():
            await dp_value.update_config()

    def is_valid(self) -> bool:
        """Return true if the configuration validated."""
        return self._is_valid

    def data_point(self, idx: int) -> TransformDataPoint:
        """Return TransformDataPoint."""
        if idx in self._data_points:
            return self._data_points[idx]

    def get_subscribe_topics(self):
        """Return subscribe topics for all datapoints."""
        topics = []
        for _, data_point in self._data_points.items():
            for topic in data_point.get_subscribe_topics():
                topics.append(topic)
        return topics

    def get_publish_topics(self):
        """Return publish topics for all datapoints."""
        topics = []
        for _, data_point in self._data_points.items():
            for topic in data_point.get_publish_topics():
                topics.append(topic)
        return topics

    def get_publish_content(self, output_topic, data=None):
        """Get publish content for all datapoints."""
        for idx, data_point in self._data_points.items():
            dp_data = data
            if data is None:
                # TODO: check change else continue
                # TODO: I don't like this dependency, rewrite
                dp_data = self._device.data_point(idx).get_mqtt_response()
            yield from data_point.get_publish_content(output_topic, dp_data)

    def set_input_payload(self, topic_parts: list, message):
        """Set the incomming data to the data points.

        message: can be str value or dict of str value
        """

        # we don't really know the topic stucture
        # assume GC ha config was used to gen the message

        if isinstance(message, dict):
            # TODO: use map
            for idx, item in message:
                self._data_points[int(idx)].set_data(item)
            return

        if isinstance(message, bytes) and topic_parts[len(topic_parts) - 2].isnumeric():
            idx = int(topic_parts[len(topic_parts) - 2])
            self._data_points[idx].set_data(message)

    def get_gateway_payload(self):
        """Get the data gateway format."""
        dict_values = {}
        for idx, data_point in self._data_points.items():
            dict_values[idx] = data_point.get_gateway_payload()
        return dict_values
