<template>
  <city-detail :is-edit="false" />
</template>

<script>
import CityDetail from './components/CityDetail'

export default {
  name: 'CreateCity',
  components: { CityDetail }
}
</script>

