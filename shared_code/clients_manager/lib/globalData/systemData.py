#!/usr/bin/python3

# written by sqall
# twitter: https://twitter.com/sqall01
# blog: https://h4des.org
# github: https://github.com/sqall01
#
# Licensed under the GNU Affero General Public License, version 3.

import threading
from typing import Any, Dict, List, Optional
from .localObjects import Alert, AlertLevel, Manager, Node, Sensor, SensorAlert, Option, InternalState, SensorDataType


class SystemData:

    def __init__(self):

        # key: type
        self._options = dict()  # type: Dict[str, Option]

        # key: nodeId
        self._nodes = dict()  # type: Dict[int, Node]

        # key: sensorId
        self._sensors = dict()  # type: Dict[int, Sensor]

        # key: managerId
        self._managers = dict()  # type: Dict[int, Manager]

        # key: alertId
        self._alerts = dict()  # type: Dict[int, Alert]

        # key: level
        self._alert_levels = dict()  # type: Dict[int, AlertLevel]

        self._sensor_alerts = list()  # type: List[SensorAlert]

        self._data_lock = threading.Lock()

    def _alert_sanity_check(self, alert: Alert):
        # Does corresponding node exist?
        if alert.nodeId not in self._nodes.keys():
            raise ValueError("Node %d for corresponding alert %d does not exist."
                             % (alert.nodeId, alert.alertId))

        # Does corresponding node have correct type?
        if self._nodes[alert.nodeId].nodeType.lower() != "alert":
            raise ValueError("Node %d not of correct type for corresponding alert %d."
                             % (alert.nodeId, alert.alertId))

        # Do the alert levels for this alert exist?
        for alert_level in alert.alertLevels:
            if alert_level not in self._alert_levels.keys():
                raise ValueError("Alert Level %d does not exist for alert %d."
                                 % (alert_level, alert.alertId))

    def _delete_alert_by_id(self, alert_id: int):
        if alert_id in self._alerts.keys():
            self._alerts[alert_id].internal_state = InternalState.DELETED
            del self._alerts[alert_id]

    def _delete_alert_level_by_level(self, level: int):
        if level in self._alert_levels.keys():

            # Remove alert level from Alert and Sensor objects.
            for _, alert in self._alerts.items():
                if level in alert.alertLevels:
                    alert.alertLevels.remove(level)

            for _, sensor in self._sensors.items():
                if level in sensor.alertLevels:
                    sensor.alertLevels.remove(level)

            self._alert_levels[level].internal_state = InternalState.DELETED
            del self._alert_levels[level]

    def _delete_linked_objects_to_node_id(self, node_id: int):
        node_obj = self._nodes[node_id]
        if node_obj.nodeType.lower() == "alert":
            to_remove = []
            for alert_id, alert in self._alerts.items():
                if alert.nodeId == node_obj.nodeId:
                    to_remove.append(alert_id)
            for alert_id in to_remove:
                self._delete_alert_by_id(alert_id)

        elif node_obj.nodeType.lower() == "manager":
            to_remove = []
            for manager_id, manager in self._managers.items():
                if manager.nodeId == node_obj.nodeId:
                    to_remove.append(manager_id)
            for manager_id in to_remove:
                self._delete_manager_by_id(manager_id)

        elif node_obj.nodeType.lower() in ["sensor", "server"]:
            to_remove = []
            for sensor_id, sensor in self._sensors.items():
                if sensor.nodeId == node_obj.nodeId:
                    to_remove.append(sensor_id)
            for sensor_id in to_remove:
                self._delete_sensor_by_id(sensor_id)

    def _delete_manager_by_id(self, manager_id: int):
        if manager_id in self._managers.keys():
            self._managers[manager_id].internal_state = InternalState.DELETED
            del self._managers[manager_id]

    def _delete_node_by_id(self, node_id: int):
        if node_id in self._nodes.keys():
            self._delete_linked_objects_to_node_id(node_id)
            self._nodes[node_id].internal_state = InternalState.DELETED
            del self._nodes[node_id]

    def _delete_option_by_type(self, option_type: int):
        if option_type in self._options.keys():
            self._options[option_type].internal_state = InternalState.DELETED
            del self._options[option_type]

    def _delete_sensor_by_id(self, sensor_id: int):
        if sensor_id in self._sensors.keys():
            # Remove Sensor Alerts for this sensor.
            for sensor_alert in list(self._sensor_alerts):
                if sensor_alert.sensorId == sensor_id:
                    sensor_alert.internal_state = InternalState.DELETED
                    self._sensor_alerts.remove(sensor_alert)

            self._sensors[sensor_id].internal_state = InternalState.DELETED
            del self._sensors[sensor_id]

    def _manager_sanity_check(self, manager: Manager):
        # Does corresponding node exist?
        if manager.nodeId not in self._nodes.keys():
            raise ValueError("Node %d for corresponding manager %d does not exist."
                             % (manager.nodeId, manager.managerId))

        # Does corresponding node have correct type?
        if self._nodes[manager.nodeId].nodeType.lower() != "manager":
            raise ValueError("Node %d not of correct type for corresponding manager %d."
                             % (manager.nodeId, manager.managerId))

    def _sensor_sanity_check(self, sensor: Sensor):
        # Does corresponding node exist?
        if sensor.nodeId not in self._nodes.keys():
            raise ValueError("Node %d for corresponding sensor %d does not exist."
                             % (sensor.nodeId, sensor.sensorId))

        # Does corresponding node have correct type?
        if self._nodes[sensor.nodeId].nodeType.lower() not in ["sensor", "server"]:
            raise ValueError("Node %d not of correct type for corresponding sensor %d."
                             % (sensor.nodeId, sensor.sensorId))

        # Do the alert levels for this alert exist?
        for alert_level in sensor.alertLevels:
            if alert_level not in self._alert_levels.keys():
                raise ValueError("Alert Level %d does not exist for sensor %d."
                                 % (alert_level, sensor.sensorId))

    def add_sensor_alert(self, sensor_alert: SensorAlert):
        """
        Adds the sensor alert and updates sensor data accordingly.
        :param sensor_alert:
        """
        # Sanity check if Alert Levels of Sensor Alert exist.
        for alert_level in sensor_alert.alertLevels:
            if alert_level not in self._alert_levels.keys():
                raise ValueError("Alert Level %d corresponding to sensor alert does not exist."
                                 % alert_level)

        # Sensor Alert is set to -1 if are rulesActivated.
        if sensor_alert.sensorId != -1:

            # Sanity check if sensor exists.
            sensor = self.get_sensor_by_id(sensor_alert.sensorId)
            if sensor is None:
                raise ValueError("Sensor %d corresponding to sensor alert does not exist."
                                 % sensor_alert.sensorId)

            # Sanity check if sensor handles received alert level.
            for alert_level in sensor_alert.alertLevels:
                if alert_level not in sensor.alertLevels:
                    raise ValueError("Sensor %d does not handle Alert Level %d."
                                     % (sensor_alert.sensorId, alert_level))

            # Sanity check if data type is correct.
            if sensor.dataType != sensor_alert.dataType:
                raise ValueError("Sensor %d corresponding to sensor alert has different data type"
                                 % sensor_alert.sensorId)

            # Update sensor data accordingly.
            with self._data_lock:
                if sensor_alert.changeState:
                    sensor.state = sensor_alert.state

                if sensor_alert.hasLatestData:
                    sensor.data = sensor_alert.sensorData

        with self._data_lock:
            sensor_alert.internal_state = InternalState.STORED

            # Make sure Sensor Alerts are ordered by time received.
            idx = 0
            for i in range(len(self._sensor_alerts), 0, -1):
                curr_sensor_alert = self._sensor_alerts[i-1]
                if curr_sensor_alert.timeReceived <= sensor_alert.timeReceived:
                    idx = i
                    break
            self._sensor_alerts.insert(idx, sensor_alert)

    def delete_alert_by_id(self, alert_id: int):
        """
        Deletes Alert object given by id.
        :param alert_id:
        """
        with self._data_lock:
            self._delete_alert_by_id(alert_id)

    def delete_alert_level_by_level(self, level: int):
        """
        Deletes Alert Level object given by level.
        :param level:
        """
        with self._data_lock:
            self._delete_alert_level_by_level(level)

    def delete_manager_by_id(self, manager_id: int):
        """
        Deletes Manager object given by id.
        :param manager_id:
        """
        with self._data_lock:
            self._delete_manager_by_id(manager_id)

    def delete_node_by_id(self, node_id: int):
        """
        Deletes Node object given by id and all linked objects to this node.
        :param node_id:
        """
        with self._data_lock:
            self._delete_node_by_id(node_id)

    def delete_option_by_type(self, option_type: int):
        """
        Deletes Option object given by type.
        :param option_type:
        """
        with self._data_lock:
            self._delete_option_by_type(option_type)

    def delete_sensor_alerts_received_before(self, timestamp: int):
        """
        Deletes all Sensor Alert objects that are older are received before the given time.
        :param timestamp:
        """
        with self._data_lock:
            for sensor_alert in list(self._sensor_alerts):
                if sensor_alert.timeReceived < timestamp:
                    sensor_alert.internal_state = InternalState.DELETED
                    self._sensor_alerts.remove(sensor_alert)

                # Sensor Alerts are ordered by time received,
                # therefore the next sensor alert will be received later in time and we can stop searching.
                else:
                    break

    def delete_sensor_by_id(self, sensor_id: int):
        """
        Deletes Sensor object given by id.
        :param sensor_id:
        """
        with self._data_lock:
            self._delete_sensor_by_id(sensor_id)

    def get_alert_by_id(self, alert_id: int) -> Optional[Alert]:
        """
        Gets Alert object corresponding to given id.
        :param alert_id:
        :return:
        """
        with self._data_lock:
            if alert_id not in self._alerts.keys():
                return None
            return self._alerts[alert_id]

    def get_alerts_by_node_id(self, node_id: int) -> List[Alert]:
        """
        Gets Alert objects corresponding to given node id.
        :param node_id:
        :return:
        """
        result = []
        node = self.get_node_by_id(node_id)
        if node is None or node.nodeType != "alert":
            return result

        with self._data_lock:
            for _, alert in self._alerts.items():
                if alert.nodeId == node_id:
                    result.append(alert)
        return result

    def get_alerts_list(self,
                        order_by_desc: bool = False) -> List[Alert]:
        """
        Gets list of all alert objects.
        :return: List of objects.
        """
        with self._data_lock:
            temp = list(self._alerts.values())
            if order_by_desc:
                temp.sort(key=lambda x: x.description.lower())
            return temp

    def get_alert_level_by_level(self, level: int) -> Optional[AlertLevel]:
        """
        Gets AlertLevel object corresponding to given id.
        :param level:
        :return:
        """
        with self._data_lock:
            if level not in self._alert_levels.keys():
                return None
            return self._alert_levels[level]

    def get_alert_levels_list(self,
                              order_by_level: bool = False) -> List[AlertLevel]:
        """
        Gets list of all alert level objects.
        :return: List of objects.
        """
        with self._data_lock:
            temp = list(self._alert_levels.values())
            if order_by_level:
                temp.sort(key=lambda x: x.level)
            return temp

    def get_manager_by_id(self, manager_id: int) -> Optional[Manager]:
        """
        Gets Manager object corresponding to given id.
        :param manager_id:
        :return:
        """
        with self._data_lock:
            if manager_id not in self._managers.keys():
                return None
            return self._managers[manager_id]

    def get_managers_by_node_id(self, node_id: int) -> List[Manager]:
        """
        Gets Manager objects corresponding to given node id.
        :param node_id:
        :return:
        """
        result = []
        node = self.get_node_by_id(node_id)
        if node is None or node.nodeType != "manager":
            return result

        with self._data_lock:
            for _, manager in self._managers.items():
                if manager.nodeId == node_id:
                    result.append(manager)
        return result

    def get_managers_list(self,
                          order_by_desc: bool = False) -> List[Manager]:
        """
        Gets list of all manager objects.
        :return: List of objects.
        """
        with self._data_lock:
            temp = list(self._managers.values())
            if order_by_desc:
                temp.sort(key=lambda x: x.description.lower())
            return temp

    def get_nodes_list(self) -> List[Node]:
        """
        Gets list of all node objects.
        :return: List of objects.
        """
        with self._data_lock:
            return list(self._nodes.values())

    def get_node_by_id(self, node_id: int) -> Optional[Node]:
        """
        Gets Node object corresponding to given id.
        :param node_id:
        :return:
        """
        with self._data_lock:
            if node_id not in self._nodes.keys():
                return None
            return self._nodes[node_id]

    def get_options_list(self) -> List[Option]:
        """
        Gets list of all option objects.
        :return: List of objects.
        """
        with self._data_lock:
            return list(self._options.values())

    def get_option_by_type(self, option_type: str) -> Optional[Option]:
        """
        Gets Option object corresponding to given type.
        :param option_type:
        :return:
        """
        with self._data_lock:
            if option_type not in self._options.keys():
                return None
            return self._options[option_type]

    def get_sensor_alerts_list(self) -> List[SensorAlert]:
        """
        Gets list of all Sensor Alert objects.
        :return: List of objects.
        """
        with self._data_lock:
            return list(self._sensor_alerts)

    def get_sensor_by_id(self, sensor_id: int) -> Optional[Sensor]:
        """
        Gets Sensor object corresponding to given id.
        :param sensor_id:
        :return:
        """
        with self._data_lock:
            if sensor_id not in self._sensors.keys():
                return None
            return self._sensors[sensor_id]

    def get_sensors_by_node_id(self, node_id: int) -> List[Sensor]:
        """
        Gets Sensor objects corresponding to given node id.
        :param node_id:
        :return:
        """
        result = []
        node = self.get_node_by_id(node_id)
        if node is None or node.nodeType != "sensor":
            return result

        with self._data_lock:
            for _, sensor in self._sensors.items():
                if sensor.nodeId == node_id:
                    result.append(sensor)
        return result

    def get_sensors_list(self,
                         order_by_desc: bool = False) -> List[Sensor]:
        """
        Gets list of all sensor objects.
        :return: List of objects.
        """
        with self._data_lock:
            temp = list(self._sensors.values())
            if order_by_desc:
                temp.sort(key=lambda x: x.description.lower())
            return temp

    def sensor_state_change(self,
                            sensor_id: int,
                            state: int,
                            data_type: SensorDataType,
                            sensor_data: Any):
        """
        Updates sensor state given by id.

        :param sensor_id:
        :param state:
        :param data_type:
        :param sensor_data:
        """
        sensor = self.get_sensor_by_id(sensor_id)
        if sensor.dataType != data_type:
            raise ValueError("Sensor %d has different data type." % sensor_id)

        with self._data_lock:
            sensor.state = state
            sensor.data = sensor_data

    def update_alert(self, alert: Alert):
        """
        Updates the given alert data.
        :param alert:
        """
        self._alert_sanity_check(alert)

        with self._data_lock:

            # Add alert object if it does not exist yet.
            if alert.alertId not in self._alerts.keys():
                self._alerts[alert.alertId] = alert
                alert.internal_state = InternalState.STORED

            # Update alert object data.
            else:
                # Do update of data instead of just using new alert object
                # to make sure others can work on the same object.
                self._alerts[alert.alertId].deepcopy(alert)

    def update_alert_level(self, alert_level: AlertLevel):
        """
        Updates the given alert level data.
        :param alert_level:
        """
        with self._data_lock:

            # Add alert level object if it does not exist yet.
            if alert_level.level not in self._alert_levels.keys():
                self._alert_levels[alert_level.level] = alert_level
                alert_level.internal_state = InternalState.STORED

            # Update alert level object data.
            else:
                # Do update of data instead of just using new alert level object
                # to make sure others can work on the same object.
                self._alert_levels[alert_level.level].deepcopy(alert_level)

    def update_manager(self, manager: Manager):
        """
        Updates the given manager data.
        :param manager:
        """
        self._manager_sanity_check(manager)

        with self._data_lock:

            # Add manager object if it does not exist yet.
            if manager.managerId not in self._managers.keys():
                self._managers[manager.managerId] = manager
                manager.internal_state = InternalState.STORED

            # Update manager object data.
            else:
                # Do update of data instead of just using new manager object
                # to make sure others can work on the same object.
                self._managers[manager.managerId].deepcopy(manager)

    def update_node(self, node: Node):
        """
        Updates the given node data.
        :param node:
        """
        with self._data_lock:

            # Add node object if it does not exist yet.
            if node.nodeId not in self._nodes.keys():
                self._nodes[node.nodeId] = node
                node.internal_state = InternalState.STORED

            # Update node object data.
            else:

                # If the type of the node has changed remove related objects.
                curr_node = self._nodes[node.nodeId]
                if curr_node.nodeType != node.nodeType:
                    self._delete_linked_objects_to_node_id(curr_node.nodeId)

                # Do update of data instead of just using new node object
                # to make sure others can work on the same object.
                self._nodes[node.nodeId].deepcopy(node)

    def update_option(self, option: Option):
        """
        Updates the given option data.
        :param option:
        :return: success of failure
        """
        with self._data_lock:

            # Add option object if it does not exist yet.
            if option.type not in self._options.keys():
                self._options[option.type] = option
                option.internal_state = InternalState.STORED

            # Update option object data.
            else:
                self._options[option.type].deepcopy(option)

    def update_sensor(self, sensor: Sensor):
        """
        Updates the given sensor data.
        :param sensor:
        """
        self._sensor_sanity_check(sensor)

        with self._data_lock:

            # Add sensor object if it does not exist yet.
            if sensor.sensorId not in self._sensors.keys():
                self._sensors[sensor.sensorId] = sensor
                sensor.internal_state = InternalState.STORED

            # Update sensor object data.
            else:
                # Do update of data instead of just using new sensor object
                # to make sure others can work on the same object.
                self._sensors[sensor.sensorId].deepcopy(sensor)
