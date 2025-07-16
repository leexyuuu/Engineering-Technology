<template>
  <area-detail :is-edit="true" />
</template>

<script>
import AreaDetail from './components/AreaDetail'

export default {
  name: 'EditForm',
  components: { AreaDetail }
}
</script>

