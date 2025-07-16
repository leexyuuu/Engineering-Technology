<template>
  <cell-detail :is-edit="true" />
</template>

<script>
import CellDetail from './components/CellDetail'

export default {
  name: 'EditForm',
  components: { CellDetail }
}
</script>

