<template>
  <comment-detail :is-edit="true" />
</template>

<script>
import CommentDetail from './components/CommentDetail'

export default {
  name: 'EditForm',
  components: { CommentDetail }
}
</script>

