<template>
  <city-detail :is-edit="true" />
</template>

<script>
import CityDetail from './components/CityDetail'

export default {
  name: 'EditForm',
  components: { CityDetail }
}
</script>

